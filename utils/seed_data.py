"""
Grabbite — Seed Data
Homepage showcase seeding for restaurants, dishes, and blogs.
Also seeds fixed demo accounts for portfolio / live-demo use.
Extracted from app.py (Plan 2 refactor).
"""
from db import db
from models import Restaurant, FoodItem, Blog, User
from utils.image_data import food_photo


def seed_homepage_showcase_data():
    """Ensure the landing page, search, restaurants, dishes, and blogs have rich demo data."""
    restaurant_rows = [
        ("Domino's", "Indiranagar, Bengaluru", "Pizza, Italian, Fast Food", "Fast cheesy pizzas, sides and family combos.", 4.6),
        ("KFC", "Koramangala, Bengaluru", "Fried Chicken, Burgers, Fast Food", "Crispy chicken buckets, burgers and snack boxes.", 4.5),
        ("McDonald's", "MG Road, Bengaluru", "Burgers, Fries, Beverages", "Classic burgers, fries, wraps and McCafe drinks.", 4.4),
        ("La Pino'z Pizza", "HSR Layout, Bengaluru", "Pizza, Pasta, Italian", "Large loaded pizzas, garlic breads and pasta.", 4.7),
        ("Pizza Hut", "Whitefield, Bengaluru", "Pizza, Italian, Desserts", "Pan pizzas, melts, sides and family meals.", 4.3),
        ("Burger King", "Jayanagar, Bengaluru", "Burgers, American, Fast Food", "Flame-grilled burgers, fries and shakes.", 4.4),
        ("Subway", "Bellandur, Bengaluru", "Sandwiches, Healthy Food, Salads", "Fresh subs, wraps and salads made your way.", 4.2),
        ("Biryani By Kilo", "Marathahalli, Bengaluru", "Biryani, North Indian, Kebabs", "Dum-cooked biryanis, kebabs and curries.", 4.8),
        ("Behrouz Biryani", "JP Nagar, Bengaluru", "Biryani, Mughlai, Desserts", "Royal layered biryanis and indulgent desserts.", 4.6),
        ("Wow! Momo", "BTM Layout, Bengaluru", "Momos, Chinese, Tibetan", "Steamed, fried and saucy momos with quick bowls.", 4.3),
        ("Haldiram's", "Rajajinagar, Bengaluru", "North Indian, Sweets, Street Food", "Indian meals, chaats, snacks and sweets.", 4.5),
        ("Barbeque Nation", "Electronic City, Bengaluru", "Barbecue, North Indian, Buffet", "Smoky grills, biryani and celebration meals.", 4.7),
        ("Starbucks", "Church Street, Bengaluru", "Coffee, Bakery, Beverages", "Signature coffees, coolers, sandwiches and bakes.", 4.4),
        ("Taco Bell", "Malleshwaram, Bengaluru", "Mexican, Fast Food, Tacos", "Crunchy tacos, burritos, nachos and rice bowls.", 4.1),
        ("Chinese Wok", "Kalyan Nagar, Bengaluru", "Chinese, Noodles, Momos", "Wok-tossed noodles, rice bowls and spicy starters.", 4.2),
        ("The Belgian Waffle Co.", "Basavanagudi, Bengaluru", "Desserts, Waffles, Ice Cream", "Fresh waffles, sundaes and dessert sandwiches.", 4.6),
        ("Chaayos", "Domlur, Bengaluru", "Tea, Snacks, Beverages", "Custom chai, sandwiches and Indian snacks.", 4.2),
        ("Natural Ice Cream", "Lavelle Road, Bengaluru", "Ice Cream, Desserts", "Fruit-based ice creams and classic scoops.", 4.8),
        ("FreshMenu", "Sarjapur Road, Bengaluru", "Healthy Food, Bowls, Continental", "Chef-crafted bowls, pasta, salads and global meals.", 4.3),
        ("Empire Restaurant", "Shivajinagar, Bengaluru", "South Indian, Rolls, Seafood", "Late-night rolls, biryani, grills and Kerala specials.", 4.5),
    ]

    restaurant_by_name = {}
    for idx, (name, location, cuisine, description, rating) in enumerate(restaurant_rows, 1):
        restaurant = Restaurant.query.filter_by(name=name).first()
        if not restaurant:
            restaurant = Restaurant(
                name=name, location=location, cuisine_type=cuisine,
                description=description, rating=rating,
                delivery_time=16 + (idx % 8) * 3,
                min_order=180 + (idx % 6) * 50,
                delivery_fee=25 + (idx % 5) * 5,
                image=food_photo(f'restaurant-{idx}', cuisine.split(',')[0].replace(' ', '+')),
                tags='trending,bestseller,delivery',
                is_active=True, is_approved=True,
            )
            db.session.add(restaurant)
            db.session.flush()
        restaurant_by_name[name] = restaurant

    dish_rows = [
        ("Domino's", "Farmhouse Feast Pizza", 399, "Pizza", True), ("Domino's", "Cheese Burst Margherita", 329, "Pizza", True),
        ("KFC", "Zinger Crunch Burger", 219, "Burger", False), ("KFC", "Hot Wings Bucket", 349, "Fast Food", False),
        ("McDonald's", "McAloo Tikki Meal", 199, "Burger", True), ("McDonald's", "McSpicy Chicken Wrap", 249, "Rolls", False),
        ("La Pino'z Pizza", "Giant Pepperoni Slice", 289, "Pizza", False), ("Pizza Hut", "Tandoori Paneer Pan Pizza", 379, "Pizza", True),
        ("Burger King", "Whopper Veg", 189, "Burger", True), ("Burger King", "Crispy Chicken Whopper", 259, "Burger", False),
        ("Subway", "Paneer Tikka Sub", 229, "Sandwiches", True), ("Subway", "Chicken Teriyaki Salad", 279, "Healthy Food", False),
        ("Biryani By Kilo", "Hyderabadi Chicken Biryani", 499, "Biryani", False), ("Biryani By Kilo", "Paneer Dum Biryani", 429, "Biryani", True),
        ("Behrouz Biryani", "Royal Mutton Biryani", 589, "Biryani", False), ("Wow! Momo", "Chicken Darjeeling Momos", 179, "Momos", False),
        ("Wow! Momo", "Veg Cheese Fried Momos", 169, "Momos", True), ("Haldiram's", "Raj Kachori", 160, "Street Food", True),
        ("Haldiram's", "Chole Bhature", 220, "North Indian", True), ("Barbeque Nation", "Smoky Grill Platter", 699, "Fast Food", False),
        ("Barbeque Nation", "Paneer Tikka Skewers", 329, "North Indian", True), ("Starbucks", "Caramel Cold Coffee", 289, "Coffee", True),
        ("Starbucks", "Smoked Chicken Croissant", 319, "Bakery", False), ("Taco Bell", "Crunchy Taco Supreme", 179, "Fast Food", True),
        ("Chinese Wok", "Schezwan Hakka Noodles", 219, "Chinese", True), ("Chinese Wok", "Chilli Garlic Fried Rice", 209, "Chinese", True),
        ("The Belgian Waffle Co.", "Dark Chocolate Waffle", 189, "Desserts", True), ("Chaayos", "Kulhad Chai Combo", 149, "Beverages", True),
        ("Natural Ice Cream", "Tender Coconut Scoop", 140, "Ice Cream", True), ("FreshMenu", "Quinoa Power Bowl", 349, "Healthy Food", True),
        ("Empire Restaurant", "Malabar Parotta Roll", 199, "Rolls", False), ("Empire Restaurant", "Kerala Fish Curry Bowl", 329, "Seafood", False),
    ]
    for idx, (restaurant_name, name, price, category, is_vegetarian) in enumerate(dish_rows, 1):
        restaurant = restaurant_by_name.get(restaurant_name)
        if restaurant and not FoodItem.query.filter_by(name=name, restaurant_id=restaurant.id).first():
            db.session.add(FoodItem(
                restaurant_id=restaurant.id, name=name, price=price,
                description=f'{name} from {restaurant_name}, prepared fresh for fast delivery.',
                category=category, image=food_photo(f'dish-{idx}', category.replace(' ', '+'), 700, 520),
                is_available=True, is_vegetarian=is_vegetarian, is_bestseller=idx <= 18,
                rating=4.1 + ((idx % 8) / 10), preparation_time=12 + (idx % 6) * 3,
                tags=f'{category},trending,{"veg" if is_vegetarian else "non-veg"}',
            ))

    blog_rows = [
        ("2026 Guide to Ordering Pizza Like a Pro", "Smart ways to pick crusts, toppings and combos for every mood.", "Pizza"),
        ("Best Biryani Styles Across India", "From Hyderabadi dum to Kolkata-style potatoes, explore regional biryani.", "Biryani"),
        ("Healthy Fast Food Swaps That Actually Taste Good", "Better bowls, salads and subs for busy weekdays.", "Healthy"),
        ("The Rise of Momos in Indian Cities", "How momos became a favourite snack from campuses to high streets.", "Street Food"),
        ("Coffee Pairings for Every Snack", "Match cold coffee, masala chai and espresso with your favourite bites.", "Beverages"),
        ("How to Build the Perfect Burger Meal", "Balance crunch, sauces, sides and drinks for the ultimate burger order.", "Fast Food"),
        ("Dessert Trends Taking Over Delivery", "Waffles, ice creams and cakes that travel beautifully.", "Desserts"),
        ("Indian Street Food Classics You Can Order Home", "Chaat, kachori, rolls and pav favourites for snack cravings.", "Street Food"),
        ("Why Cloud Kitchens Are Changing Dinner", "Fresh menus, faster dispatch and data-led comfort food.", "Food Tech"),
        ("Weekend Family Meal Planner", "Easy ordering ideas for movie nights, parties and lazy Sundays.", "Guides"),
    ]
    for idx, (title, excerpt, category) in enumerate(blog_rows, 1):
        if not Blog.query.filter_by(title=title).first():
            blog = Blog(
                title=title, excerpt=excerpt,
                content=excerpt + '\n\nGrabBite curates restaurant trends, delivery tips and menu ideas so every order feels effortless.',
                author='GrabBite Editorial',
                image=food_photo(f'blog-{idx}', category.replace(' ', '+'), 900, 560),
                category=category, status='published', featured=True,
            )
            blog.generate_slug()
            db.session.add(blog)

    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# DEMO ACCOUNTS
# ─────────────────────────────────────────────────────────────────────────────

# Passwords are stored hashed. The plaintext values below are only used once
# during seeding — they are the credentials shown in the README demo section.
_DEMO_ACCOUNTS = [
    {
        'name':     'Demo Customer',
        'email':    'demo_user@gmail.com',
        'password': 'Demo@1234',
        'role':     'customer',
        'is_admin': False,
    },
    {
        'name':     'Demo Owner',
        'email':    'owner@gmail.com',
        'password': 'Owner@1234',
        'role':     'restaurant_owner',
        'is_admin': False,
        'restaurant': {
            'name':         'Demo Kitchen',
            'location':     'Koramangala, Bengaluru',
            'cuisine_type': 'Multi-Cuisine',
            'description':  'Demo restaurant for portfolio showcase.',
            'is_active':    True,
            'is_approved':  True,
        },
    },
    {
        'name':     'Admin',
        'email':    'admin@gmail.com',
        'password': 'Admin@1234',
        'role':     'admin',
        'is_admin': True,
    },
]


def seed_demo_accounts() -> None:
    """Create fixed demo accounts on first boot if they don't already exist.

    Safe to call on every startup — skips any account whose email is already
    in the database. Also repairs existing demo accounts with wrong roles.
    Passwords are hashed with werkzeug pbkdf2:sha256.
    """
    from werkzeug.security import generate_password_hash

    for spec in _DEMO_ACCOUNTS:
        existing = User.query.filter_by(email=spec['email']).first()

        if existing:
            # Repair: fix role/is_admin if the account exists but was seeded wrong
            changed = False
            if existing.role != spec['role']:
                existing.role = spec['role']
                changed = True
            if existing.is_admin != spec.get('is_admin', False):
                existing.is_admin = spec.get('is_admin', False)
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if changed:
                db.session.commit()
                print(f'🔧 Demo account repaired: {spec["email"]}  ({spec["role"]})')
            continue

        user = User(
            name=spec['name'],
            email=spec['email'],
            password=generate_password_hash(spec['password']),
            role=spec['role'],
            is_admin=spec.get('is_admin', False),
            is_active=True,
        )
        user.generate_referral_code()
        db.session.add(user)
        db.session.flush()   # get user.id for the owner's restaurant below

        # Restaurant owners need a restaurant record so the owner dashboard works
        if spec['role'] == 'restaurant_owner' and 'restaurant' in spec:
            rest_spec = spec['restaurant']
            restaurant = Restaurant.query.filter_by(
                name=rest_spec['name']
            ).first()
            if not restaurant:
                restaurant = Restaurant(
                    owner_id=user.id,
                    **rest_spec,
                )
                db.session.add(restaurant)

        print(f'✅ Demo account seeded: {spec["email"]}  ({spec["role"]})')

    db.session.commit()
