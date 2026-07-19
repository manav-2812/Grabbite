/* Menu management enhancements */

class MenuManager {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.currentRestaurantId = null;
        this.dataTable = null;
        this.initEventListeners();
    }

    initEventListeners() {
        // Refresh menu items when modal opens
        this.modal.addEventListener('show.bs.modal', (e) => {
            const button = e.relatedTarget;
            if (button) {
                this.currentRestaurantId = button.getAttribute('data-restaurant-id');
                this.loadMenuItems();
            }
        });

        // Clear form when modal closes
        this.modal.addEventListener('hide.bs.modal', () => {
            this.hideAddItemForm();
            this.currentRestaurantId = null;
            if (this.dataTable) {
                this.dataTable.destroy();
                this.dataTable = null;
            }
        });
    }

    async loadMenuItems() {
        try {
            AdminUtils.showLoadingSpinner();
            const response = await fetch(`/admin/api/restaurant/${this.currentRestaurantId}/menu`);
            const data = await response.json();
            this.renderMenuItems(data.items);
        } catch (error) {
            console.error('Error loading menu items:', error);
            showToast('Failed to load menu items', 'error');
        } finally {
            AdminUtils.hideLoadingSpinner();
        }
    }

    renderMenuItems(items) {
        const container = document.getElementById('menuItemsTable');
        if (!container) {
            console.error('Menu items container not found');
            return;
        }

        // Create table if it doesn't exist
        if (!this.dataTable) {
            container.innerHTML = `
                <table class="table table-striped" id="menuItemsDataTable">
                    <thead>
                        <tr>
                            <th>Image</th>
                            <th>Name</th>
                            <th>Category</th>
                            <th>Price</th>
                            <th>Availability</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map(item => this.createMenuItemRow(item)).join('')}
                    </tbody>
                </table>
            `;

            // Initialize DataTable
            this.dataTable = new DataTable('#menuItemsDataTable', {
                pageLength: 5,
                lengthMenu: [5, 10, 25],
                order: [[1, 'asc']], // Sort by name by default
                columnDefs: [
                    { orderable: false, targets: [0, 5] }, // Disable sorting for image and actions columns
                    { searchable: false, targets: [0, 4, 5] } // Disable search for image, availability toggle, and actions
                ]
            });
        } else {
            // Update existing table
            this.dataTable.clear();
            items.forEach(item => {
                this.dataTable.row.add($(this.createMenuItemRow(item)));
            });
            this.dataTable.draw();
        }

        // Initialize availability toggles
        items.forEach(item => {
            const toggle = document.querySelector(`#availability-${item.id}`);
            if (toggle) {
                toggle.addEventListener('change', () => this.toggleAvailability(item.id, toggle.checked));
            }
        });
    }

    createMenuItemRow(item) {
        return `
            <tr>
                <td>
                    <img src="${item.image || '/static/img/food-default.jpg'}" 
                         alt="${item.name}" 
                         class="menu-item-image"
                         style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">
                </td>
                <td>
                    <div>${item.name}</div>
                    <small class="text-muted">${item.description || ''}</small>
                </td>
                <td>${item.category}</td>
                <td>${AdminUtils.formatCurrency(item.price)}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" role="switch" 
                               id="availability-${item.id}" 
                               ${item.is_available ? 'checked' : ''}>
                    </div>
                </td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-primary" onclick="editMenuItem(${item.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteMenuItem(${item.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    async toggleAvailability(itemId, isAvailable) {
        try {
            const response = await AdminUtils.updateResource(`/admin/api/menu-item/${itemId}`, {
                is_available: isAvailable
            });
            if (response.success) {
                showToast(`Item ${isAvailable ? 'enabled' : 'disabled'} successfully`, 'success');
            }
        } catch (error) {
            console.error('Error toggling availability:', error);
            showToast('Failed to update item availability', 'error');
            // Revert toggle state
            const toggle = document.querySelector(`#availability-${itemId}`);
            if (toggle) toggle.checked = !isAvailable;
        }
    }

    showAddItemForm() {
        const form = document.getElementById('addItemForm');
        form.style.display = 'block';
        form.scrollIntoView({ behavior: 'smooth' });

        // Reset form and preview
        const menuItemForm = document.getElementById('menuItemForm');
        menuItemForm.reset();
        menuItemForm.querySelector('.btn-primary').textContent = 'Add Item';
        const preview = document.getElementById('menuItemImagePreview');
        if (preview) {
            preview.style.display = 'none';
            preview.src = '';
        }
    }

    hideAddItemForm() {
        const form = document.getElementById('addItemForm');
        form.style.display = 'none';
        document.getElementById('menuItemForm').reset();
    }

    validateMenuItemForm(form) {
        const requiredFields = ['name', 'price', 'category'];
        let isValid = true;

        // Reset previous validation state
        form.querySelectorAll('.is-invalid').forEach(field => {
            field.classList.remove('is-invalid');
        });

        // Validate required fields
        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            }
        });

        // Validate price
        const priceField = form.querySelector('[name="price"]');
        if (priceField.value && (isNaN(priceField.value) || parseFloat(priceField.value) <= 0)) {
            priceField.classList.add('is-invalid');
            isValid = false;
        }

        // Validate image if selected
        const imageInput = form.querySelector('[name="image"]');
        if (imageInput.files.length > 0) {
            const file = imageInput.files[0];
            if (!file.type.startsWith('image/')) {
                imageInput.classList.add('is-invalid');
                showToast('Please select a valid image file', 'error');
                isValid = false;
            } else if (file.size > 5 * 1024 * 1024) {
                imageInput.classList.add('is-invalid');
                showToast('Image file size should be less than 5MB', 'error');
                isValid = false;
            }
        }

        return isValid;
    }

    async submitMenuItem(form) {
        if (!this.validateMenuItemForm(form)) {
            return;
        }

        const formData = AdminUtils.serializeForm(form);
        const itemId = form.dataset.itemId;
        const isEdit = !!itemId;

        if (!isEdit) {
            formData.append('restaurant_id', this.currentRestaurantId);
        }

        try {
            AdminUtils.showLoadingSpinner();

            const response = await (isEdit ?
                AdminUtils.updateResource(`/admin/api/menu-item/${itemId}`, formData) :
                AdminUtils.createResource('/admin/api/menu-item', formData));

            showToast(`Menu item ${isEdit ? 'updated' : 'added'} successfully`, 'success');
            this.hideAddItemForm();
            this.loadMenuItems();
        } catch (error) {
            console.error('Error submitting menu item:', error);
            showToast(`Failed to ${isEdit ? 'update' : 'add'} menu item`, 'error');
        } finally {
            AdminUtils.hideLoadingSpinner();
        }
    }

}

// Initialize the menu manager
document.addEventListener('DOMContentLoaded', () => {
    window.menuManager = new MenuManager('menuModal');
});