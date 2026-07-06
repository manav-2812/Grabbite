"""
Grabbite — Admin: Blog Management
/admin/blogs/*, /admin/api/blog/*
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from db import db
from models import Blog
from blueprints.admin import admin, save_image, log_admin_activity
from utils.decorators import admin_required


@admin.route('/blogs')
@login_required
@admin_required
def admin_blogs():
    blog_list = Blog.query.order_by(Blog.created_at.desc()).all()
    return render_template('admin/blogs.html', blogs=blog_list)


# Alias expected by some broadcast redirects
admin_blogs_list = admin_blogs


@admin.route('/blogs/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_blog():
    if request.method == 'POST':
        try:
            image_filename = 'blog_default.jpg'
            if 'image' in request.files:
                saved, _ = save_image(request.files['image'])
                if saved:
                    image_filename = saved

            blog = Blog(
                title=request.form.get('title'),
                content=request.form.get('content'),
                excerpt=request.form.get('excerpt', ''),
                author=current_user.name,
                category=request.form.get('category', 'Food'),
                status=request.form.get('status', 'published'),
                featured=request.form.get('featured') == 'on',
                image=image_filename,
            )
            blog.generate_slug()
            db.session.add(blog)
            db.session.commit()
            log_admin_activity('Added Blog', 'blog', blog.id, f'Added: {blog.title}')
            flash('Blog post added successfully!', 'success')
            return redirect(url_for('admin.admin_blogs'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding blog: {str(e)}', 'error')

    return render_template('admin/add_blog.html')


@admin.route('/blogs/edit/<int:blog_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog(blog_id):
    blog = Blog.query.get_or_404(blog_id)

    if request.method == 'POST':
        try:
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], blog.image)
                if saved:
                    blog.image = saved

            blog.title    = request.form.get('title', blog.title)
            blog.content  = request.form.get('content', blog.content)
            blog.excerpt  = request.form.get('excerpt', blog.excerpt)
            blog.category = request.form.get('category', blog.category)
            blog.status   = request.form.get('status', blog.status)
            blog.featured = request.form.get('featured') == 'on'

            db.session.commit()
            log_admin_activity('Updated Blog', 'blog', blog.id)
            flash('Blog updated successfully!', 'success')
            return redirect(url_for('admin.admin_blogs'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating blog: {str(e)}', 'error')

    return render_template('admin/edit_blog.html', blog=blog)


@admin.route('/blogs/delete/<int:blog_id>', methods=['POST'])
@login_required
@admin_required
def delete_blog(blog_id):
    try:
        blog  = Blog.query.get_or_404(blog_id)
        title = blog.title
        db.session.delete(blog)
        db.session.commit()
        log_admin_activity('Deleted Blog', 'blog', blog_id, f'Deleted: {title}')
        flash('Blog deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting blog: {str(e)}', 'error')
    return redirect(url_for('admin.admin_blogs'))


@admin.route('/api/blog', methods=['POST'])
@login_required
@admin_required
def api_add_blog():
    try:
        filename = 'blog_default.jpg'
        if 'image' in request.files:
            saved, _ = save_image(request.files['image'])
            if saved:
                filename = saved

        blog = Blog(
            title=request.form.get('title'),
            content=request.form.get('content'),
            author=current_user.name,
            excerpt=request.form.get('excerpt', ''),
            category=request.form.get('category', 'Food'),
            status='published',
            image=filename,
        )
        blog.generate_slug()
        db.session.add(blog)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Blog added', 'id': blog.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/blog/<int:blog_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_blog(blog_id):
    if request.method == 'GET':
        b = Blog.query.get_or_404(blog_id)
        return jsonify({'id': b.id, 'title': b.title, 'content': b.content,
                        'author': b.author, 'excerpt': b.excerpt,
                        'category': b.category, 'image': b.image, 'status': b.status})

    elif request.method == 'PUT':
        try:
            b = Blog.query.get_or_404(blog_id)
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], b.image)
                if saved:
                    b.image = saved
            b.title    = request.form.get('title', b.title)
            b.content  = request.form.get('content', b.content)
            b.excerpt  = request.form.get('excerpt', b.excerpt)
            b.category = request.form.get('category', b.category)
            b.status   = request.form.get('status', b.status)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            b = Blog.query.get_or_404(blog_id)
            db.session.delete(b)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
