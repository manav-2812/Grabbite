"""
Grabbite — Public Blueprint
HIGH-4: Extracted from app.py as part of the blueprint refactor.
Handles all publicly-accessible pages and pages that require login but are
user-facing (not admin/owner).
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, abort, current_app)
from flask_login import current_user, login_required
from collections import OrderedDict

from db import db
from models import (Restaurant, FoodItem, Blog, Notification, Offer,
                    Wishlist, Review)

public_bp = Blueprint('public', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# STATIC DATA — gallery dish catalogue, static offers
# (kept here so api_search can import _DISHES from this module)
# ─────────────────────────────────────────────────────────────────────────────
_static_offers = {
    1: {'id': 1, 'title': '50% OFF First Order',
        'description': 'Get 50% OFF on your first order. Max discount ₹200.',
        'terms': ['Valid on first order only', 'Max discount ₹200', 'Not stackable'],
        'code': 'WELCOME50', 'valid_until': 'Ongoing',
        'image': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80',
        'restaurants': ['All Restaurants']},
    2: {'id': 2, 'title': 'Free Delivery',
        'description': 'Free delivery on orders above ₹399.',
        'terms': ['Min order ₹399', 'All restaurants', 'No code needed'],
        'code': 'FREEDEL', 'valid_until': 'Ongoing',
        'image': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&q=80',
        'restaurants': ['All Restaurants']},
}

# Static dish catalogue used by gallery and dish_detail pages
_DISHES = {
    # ── Curries & Mains ────────────────────────────────────────────────────
    1:  {'id': 1,  'category': 'Curries & Mains',    'restaurant': 'Spice Garden',
         'name': 'Butter Chicken',    'price': 250,
         'image': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600&q=80',
         'desc': 'Rich, creamy tomato-butter curry with tender tandoori chicken.',
         'details': 'Marinated overnight in yoghurt and spices, the chicken is first grilled in a tandoor and then slow-cooked in a silky, mildly spiced tomato-cream sauce. Perfect with garlic naan or steamed basmati.',
         'tags': ['Non-Veg', 'Curry', 'North Indian'], 'calories': '420 kcal', 'prep_time': '30 min'},
    5:  {'id': 5,  'category': 'Curries & Mains',    'restaurant': 'Spice Garden',
         'name': 'Palak Paneer',      'price': 220,
         'image': 'https://images.unsplash.com/photo-1618449840665-9ed506d73a34?w=600&q=80',
         'desc': 'Smooth spinach gravy packed with cubes of fresh cottage cheese.',
         'details': 'Blanched spinach blended into a velvety purée, seasoned with cumin, garlic and cream, then loaded with cubes of fresh cottage cheese. A powerhouse of iron and protein that tastes indulgent.',
         'tags': ['Veg', 'Curry', 'North Indian'], 'calories': '340 kcal', 'prep_time': '30 min'},
    11: {'id': 11, 'category': 'Curries & Mains',    'restaurant': 'Spice Garden',
         'name': 'Malai Kofta',       'price': 200,
         'image': 'https://images.unsplash.com/photo-1574653853027-5382a3d23a15?w=600&q=80',
         'desc': 'Fried paneer-potato dumplings in a velvety cashew-tomato gravy.',
         'details': 'Delicate dumplings made from mashed paneer, potato and raisins, deep-fried and dunked into a velvety cashew-tomato gravy enriched with cream and mild spices. Restaurant royalty on your plate.',
         'tags': ['Veg', 'Curry', 'North Indian'], 'calories': '460 kcal', 'prep_time': '40 min'},
    13: {'id': 13, 'category': 'Curries & Mains',    'restaurant': 'Tandoor Tales',
         'name': 'Chicken Curry',     'price': 180,
         'image': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80',
         'desc': 'Bone-in chicken slow-cooked in a deeply spiced onion-tomato masala.',
         'details': 'Bone-in chicken pieces slow-cooked in a deeply spiced masala of caramelised onions, ripe tomatoes, ginger-garlic paste and whole spices. The long cook time creates an intensely flavourful, rich gravy.',
         'tags': ['Non-Veg', 'Curry', 'Indian'], 'calories': '390 kcal', 'prep_time': '35 min'},
    15: {'id': 15, 'category': 'Curries & Mains',    'restaurant': 'Spice Garden',
         'name': 'Kadhai Paneer',     'price': 220,
         'image': 'https://images.unsplash.com/photo-1631452180775-6e5f5a9d3b1a?w=600&q=80',
         'desc': 'Paneer and capsicum tossed in a smoky, rustic kadhai masala.',
         'details': 'Paneer and colourful capsicum tossed in a rustic, chunky kadhai masala made with freshly ground coriander and dried chillies. The kadhai (wok) cooking method lends a distinct charred, smoky flavour.',
         'tags': ['Veg', 'Curry', 'North Indian'], 'calories': '370 kcal', 'prep_time': '25 min'},
    17: {'id': 17, 'category': 'Curries & Mains',    'restaurant': 'Coastal Cravings',
         'name': 'Fish Curry',        'price': 200,
         'image': 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80',
         'desc': 'Tangy coconut-tamarind fish curry from the coastal kitchens of Goa.',
         'details': 'Firm fish fillets simmered in a tangy, fiery coconut-tamarind gravy tempered with mustard seeds, curry leaves and kokum. A staple from the coastal kitchens of Goa and Kerala. Best with steamed rice.',
         'tags': ['Non-Veg', 'Curry', 'Coastal'], 'calories': '360 kcal', 'prep_time': '30 min'},
    21: {'id': 21, 'category': 'Curries & Mains',    'restaurant': 'Spice Garden',
         'name': 'Dal Makhani',       'price': 180,
         'image': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&q=80',
         'desc': 'Slow-cooked black lentils in a rich buttery tomato sauce — a Punjabi legend.',
         'details': 'Black urad dal and kidney beans simmered overnight on a low flame with butter, cream and whole spices until gloriously rich. Dal Makhani is the crown jewel of Punjabi cuisine, perfect with naan or paratha.',
         'tags': ['Veg', 'Dal', 'Punjabi'], 'calories': '380 kcal', 'prep_time': '45 min'},
    22: {'id': 22, 'category': 'Curries & Mains',    'restaurant': 'Tandoor Tales',
         'name': 'Rogan Josh',        'price': 300,
         'image': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600&q=80',
         'desc': 'Slow-braised Kashmiri lamb curry with aromatic whole spices and Kashmiri chillies.',
         'details': 'Tender lamb shoulder braised in a fragrant sauce of Kashmiri chillies, fennel, ginger and whole spices. The dish gets its characteristic deep-red colour from Kashmiri mirchi — no tomatoes are used.',
         'tags': ['Non-Veg', 'Curry', 'Kashmiri'], 'calories': '520 kcal', 'prep_time': '60 min'},
    23: {'id': 23, 'category': 'Curries & Mains',    'restaurant': 'Coastal Cravings',
         'name': 'Prawn Masala',      'price': 320,
         'image': 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80',
         'desc': 'Juicy prawns cooked in a fiery coastal tomato-coconut masala.',
         'details': 'Tiger prawns sautéed with onion, green chilli and a thick coconut-tomato masala bursting with coastal spices. Served with steamed rice or appam. A coastal feast on every plate.',
         'tags': ['Non-Veg', 'Seafood', 'Coastal'], 'calories': '340 kcal', 'prep_time': '25 min'},

    # ── Rice & Biryani ─────────────────────────────────────────────────────
    6:  {'id': 6,  'category': 'Rice & Biryani',     'restaurant': 'Biryani House',
         'name': 'Hyderabadi Biryani','price': 280,
         'image': 'https://images.unsplash.com/photo-1563379091339-03b246963d29?w=600&q=80',
         'desc': 'Dum-cooked saffron biryani with marinated meat — a royal Hyderabadi classic.',
         'details': 'Dum-cooked in a sealed handi, fragrant basmati rice is layered with succulent slow-marinated mutton, whole spices, fried onions and saffron-infused milk. Served with raita and mirchi ka salan.',
         'tags': ['Non-Veg', 'Rice', 'Hyderabadi'], 'calories': '620 kcal', 'prep_time': '60 min'},
    7:  {'id': 7,  'category': 'Rice & Biryani',     'restaurant': 'Biryani House',
         'name': 'Rajma Chawal',      'price': 160,
         'image': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&q=80',
         'desc': 'Creamy kidney-bean curry served over fluffy steamed basmati rice.',
         'details': 'Red kidney beans simmered low-and-slow in a thick onion-tomato gravy spiced with coriander, cumin and garam masala. Served over fluffy steamed basmati with a dollop of ghee on top.',
         'tags': ['Veg', 'Punjabi', 'Comfort Food'], 'calories': '400 kcal', 'prep_time': '40 min'},
    24: {'id': 24, 'category': 'Rice & Biryani',     'restaurant': 'Biryani House',
         'name': 'Veg Biryani',       'price': 200,
         'image': 'https://images.unsplash.com/photo-1645177628172-a94c1f96debb?w=600&q=80',
         'desc': 'Fragrant basmati rice dum-cooked with seasonal vegetables and whole spices.',
         'details': 'A mélange of fresh seasonal vegetables — carrots, beans, potatoes and peas — layered with long-grain basmati and sealed with a dough lid. Slow-cooked until the flavours meld into a celebration of aromas.',
         'tags': ['Veg', 'Rice', 'Biryani'], 'calories': '480 kcal', 'prep_time': '50 min'},
    25: {'id': 25, 'category': 'Rice & Biryani',     'restaurant': 'Biryani House',
         'name': 'Chicken Biryani',   'price': 260,
         'image': 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80',
         'desc': 'Juicy chicken marinated in yoghurt and spices, dum-cooked with basmati rice.',
         'details': "Bone-in chicken pieces marinated for 4 hours in yoghurt, lemon and biryani spices, then layered with half-cooked basmati and sealed for dum cooking. Every grain absorbs the chicken's rich flavours.",
         'tags': ['Non-Veg', 'Rice', 'Biryani'], 'calories': '580 kcal', 'prep_time': '55 min'},
    26: {'id': 26, 'category': 'Rice & Biryani',     'restaurant': 'Biryani House',
         'name': 'Egg Fried Rice',    'price': 130,
         'image': 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80',
         'desc': 'Wok-tossed basmati with scrambled eggs, spring onion and soy sauce.',
         'details': 'Day-old basmati rice tossed in a blazing wok with beaten egg, fresh ginger, garlic, soy sauce, spring onions and a dash of sesame oil. Fast, satisfying and endlessly craveable.',
         'tags': ['Non-Veg', 'Rice', 'Chinese-Indian'], 'calories': '380 kcal', 'prep_time': '15 min'},

    # ── South Indian ───────────────────────────────────────────────────────
    4:  {'id': 4,  'category': 'South Indian',       'restaurant': 'Dosa Corner',
         'name': 'Masala Dosa',       'price': 150,
         'image': 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&q=80',
         'desc': 'Golden crispy dosa filled with spiced potato masala, with sambhar and chutney.',
         'details': 'Fermented rice-and-lentil batter spread thin on a hot griddle to produce a golden, lacy crepe stuffed with a turmeric-kissed potato masala. Comes with two chutneys and a bowl of piping hot sambhar.',
         'tags': ['Veg', 'South Indian', 'Breakfast'], 'calories': '290 kcal', 'prep_time': '25 min'},
    19: {'id': 19, 'category': 'South Indian',       'restaurant': 'Dosa Corner',
         'name': 'Idli Sambhar',      'price': 100,
         'image': 'https://images.unsplash.com/photo-1630383249896-424e482df921?w=600&q=80',
         'desc': 'Pillowy steamed rice cakes with lentil soup and coconut chutney.',
         'details': 'Pillowy-soft, fermented rice-and-lentil cakes steamed to perfection, paired with a hearty toor dal sambhar loaded with vegetables and a smooth coconut-and-coriander chutney. A wholesome South Indian classic.',
         'tags': ['Veg', 'South Indian', 'Breakfast'], 'calories': '240 kcal', 'prep_time': '20 min'},
    27: {'id': 27, 'category': 'South Indian',       'restaurant': 'Dosa Corner',
         'name': 'Uttapam',           'price': 120,
         'image': 'https://images.unsplash.com/photo-1695654398248-a7bba94e05bd?w=600&q=80',
         'desc': 'Thick, soft rice pancake topped with onions, tomatoes and green chillies.',
         'details': 'A thick, spongy dosa variant topped generously with diced onions, tomatoes, green chillies and coriander before being cooked on a griddle. Mild and filling, it pairs beautifully with sambhar and chutney.',
         'tags': ['Veg', 'South Indian', 'Breakfast'], 'calories': '270 kcal', 'prep_time': '20 min'},
    28: {'id': 28, 'category': 'South Indian',       'restaurant': 'Dosa Corner',
         'name': 'Medu Vada',         'price': 80,
         'image': 'https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?w=600&q=80',
         'desc': 'Crispy urad dal doughnuts, golden on the outside, fluffy inside.',
         'details': 'Fermented urad dal batter shaped into ring doughnuts and deep-fried until crisp. The crunchy exterior gives way to a soft, airy centre. Dunked in sambhar and eaten with coconut chutney — pure bliss.',
         'tags': ['Veg', 'South Indian', 'Snack'], 'calories': '220 kcal', 'prep_time': '15 min'},
    29: {'id': 29, 'category': 'South Indian',       'restaurant': 'Dosa Corner',
         'name': 'Appam with Stew',   'price': 160,
         'image': 'https://images.unsplash.com/photo-1630935645565-f7b65dd29946?w=600&q=80',
         'desc': 'Lacy fermented rice pancake served with a light coconut milk vegetable stew.',
         'details': 'Bowl-shaped rice hoppers with crispy, lacy edges and a soft, spongy centre, served alongside a fragrant Kerala-style stew of vegetables simmered in coconut milk with whole spices.',
         'tags': ['Veg', 'South Indian', 'Kerala'], 'calories': '300 kcal', 'prep_time': '30 min'},

    # ── Snacks & Street Food ───────────────────────────────────────────────
    8:  {'id': 8,  'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Dhokla',            'price': 120,
         'image': 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&q=80',
         'desc': 'Steamed, spongy gram-flour snack from Gujarat with a mustard seed tadka.',
         'details': 'Fermented chickpea flour batter steamed into soft, airy squares and tempered with a tadka of mustard seeds, curry leaves and green chilli. Finished with fresh coconut and coriander. Guilt-free snacking!',
         'tags': ['Veg', 'Snack', 'Gujarati'], 'calories': '200 kcal', 'prep_time': '20 min'},
    12: {'id': 12, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Vada Pav',          'price': 60,
         'image': 'https://images.unsplash.com/photo-1606755962773-d324e0a13086?w=600&q=80',
         'desc': "Mumbai's iconic spicy potato fritter stuffed in a soft bread roll.",
         'details': 'A spiced potato dumpling coated in chickpea-flour batter and deep-fried to a crisp, sandwiched in a soft pav roll with layers of dry garlic chutney, green chutney and a smear of tamarind. Mumbai at its finest.',
         'tags': ['Veg', 'Street Food', 'Maharashtrian'], 'calories': '310 kcal', 'prep_time': '20 min'},
    14: {'id': 14, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Samosa',            'price': 40,
         'image': 'https://images.unsplash.com/photo-1601050690117-94f5f6fa8bd7?w=600&q=80',
         'desc': 'Crispy triangular pastry stuffed with spiced potato and peas.',
         'details': 'Flaky, triangular pastry shells packed with a filling of mashed potato, green peas and aromatic spices including cumin, coriander and amchur. Fried golden and served piping hot with tamarind and mint chutneys.',
         'tags': ['Veg', 'Street Food', 'Snack'], 'calories': '260 kcal', 'prep_time': '30 min'},
    16: {'id': 16, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Pav Bhaji',         'price': 150,
         'image': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80',
         'desc': 'Buttery spiced vegetable mash with toasted pav rolls — Mumbai street royalty.',
         'details': 'A medley of mashed potatoes, cauliflower, peas and capsicum cooked on a flat iron tawa with a special pav bhaji masala and a generous knob of butter, served with toasted, buttered pav rolls.',
         'tags': ['Veg', 'Street Food', 'Maharashtrian'], 'calories': '430 kcal', 'prep_time': '25 min'},
    18: {'id': 18, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Pani Puri',         'price': 80,
         'image': 'https://images.unsplash.com/photo-1613292443284-8d10ef9383fe?w=600&q=80',
         'desc': 'Crispy hollow puris filled with spicy tangy water and potato-chickpea mix.',
         'details': 'Bite-sized semolina spheres puffed hollow and fried until irresistibly crisp, stuffed with a spiced potato-chickpea filling and dunked in a tangy, minty, iced pani. One puri is never enough!',
         'tags': ['Veg', 'Street Food', 'Chaat'], 'calories': '180 kcal', 'prep_time': '20 min'},
    30: {'id': 30, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Bhel Puri',         'price': 70,
         'image': 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&q=80',
         'desc': 'Crunchy puffed rice tossed with sev, chutneys, onion and raw mango.',
         'details': "A carnival of textures — puffed rice, sev, chopped onion, raw mango, boiled potato and a drizzle of sweet tamarind and spicy green chutney. Mumbai's most beloved beach-side snack, ready in minutes.",
         'tags': ['Veg', 'Street Food', 'Chaat'], 'calories': '150 kcal', 'prep_time': '10 min'},
    31: {'id': 31, 'category': 'Snacks & Street Food','restaurant': 'Mumbai Masala',
         'name': 'Aloo Tikki',        'price': 60,
         'image': 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80',
         'desc': 'Crispy spiced potato patties topped with yoghurt and tangy chutneys.',
         'details': "Mashed potato cakes seasoned with cumin, green chilli and chaat masala, pan-fried until golden and crispy, then topped with beaten yoghurt, tamarind chutney and fresh coriander. A true chaat lover's delight.",
         'tags': ['Veg', 'Street Food', 'Chaat'], 'calories': '230 kcal', 'prep_time': '15 min'},
    32: {'id': 32, 'category': 'Snacks & Street Food','restaurant': 'Spice Garden',
         'name': 'Spring Rolls',      'price': 120,
         'image': 'https://images.unsplash.com/photo-1607330289024-1535c6b4e1c1?w=600&q=80',
         'desc': 'Crispy rolls stuffed with stir-fried vegetables and glass noodles.',
         'details': 'Paper-thin wrappers encasing a filling of stir-fried cabbage, carrots, glass noodles and spring onion, seasoned with soy and sesame. Deep-fried until shatteringly crisp. Perfect with sweet chilli sauce.',
         'tags': ['Veg', 'Snack', 'Chinese'], 'calories': '210 kcal', 'prep_time': '20 min'},

    # ── Non-Veg Specials ───────────────────────────────────────────────────
    2:  {'id': 2,  'category': 'Non-Veg Specials',  'restaurant': 'Tandoor Tales',
         'name': 'Paneer Tikka',      'price': 220,
         'image': 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=600&q=80',
         'desc': 'Smoky grilled paneer skewers marinated in a vibrant tandoori yoghurt.',
         'details': 'Fresh cottage cheese cubes skewered with bell peppers and onions, coated in a vibrant tandoori marinade and char-grilled to smoky perfection. Served with mint chutney and lemon.',
         'tags': ['Veg', 'Starter', 'North Indian'], 'calories': '310 kcal', 'prep_time': '20 min'},
    33: {'id': 33, 'category': 'Non-Veg Specials',  'restaurant': 'Tandoor Tales',
         'name': 'Chicken Tandoori',  'price': 280,
         'image': 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=600&q=80',
         'desc': 'Whole chicken legs marinated in yoghurt and spices, roasted in a clay oven.',
         'details': 'Chicken legs scored deep and marinated for 8 hours in a blend of yoghurt, Kashmiri chilli, garam masala and mustard oil. Roasted in a 450 °C tandoor until charred on the outside and juicy within.',
         'tags': ['Non-Veg', 'Tandoor', 'North Indian'], 'calories': '490 kcal', 'prep_time': '30 min'},
    34: {'id': 34, 'category': 'Non-Veg Specials',  'restaurant': 'Tandoor Tales',
         'name': 'Mutton Seekh Kebab','price': 260,
         'image': 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=600&q=80',
         'desc': 'Minced mutton kebabs with fresh herbs, grilled on iron skewers.',
         'details': 'Finely minced mutton mixed with onion, green chilli, fresh coriander, mint and warm spices, moulded onto flat skewers and grilled in a tandoor. Smoky, juicy and irresistibly fragrant.',
         'tags': ['Non-Veg', 'Kebab', 'Tandoor'], 'calories': '420 kcal', 'prep_time': '25 min'},
    35: {'id': 35, 'category': 'Non-Veg Specials',  'restaurant': 'Coastal Cravings',
         'name': 'Butter Garlic Crab','price': 450,
         'image': 'https://images.unsplash.com/photo-1608500218807-c53c581b44ac?w=600&q=80',
         'desc': 'Whole crab cooked in a buttery garlic and pepper sauce — coastal indulgence.',
         'details': 'Fresh mud crab cracked open and slow-cooked in a decadent sauce of melted butter, roasted garlic, black pepper and parsley. An unabashedly indulgent seafood dish for the true crab lover.',
         'tags': ['Non-Veg', 'Seafood', 'Coastal'], 'calories': '510 kcal', 'prep_time': '35 min'},
    36: {'id': 36, 'category': 'Non-Veg Specials',  'restaurant': 'Tandoor Tales',
         'name': 'Egg Bhurji',        'price': 100,
         'image': 'https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&q=80',
         'desc': 'Spiced Indian-style scrambled eggs with onion, tomato and fresh coriander.',
         'details': 'Beaten eggs tossed in a sizzling pan with finely chopped onion, tomato, green chilli, cumin and a pinch of turmeric. Finished with fresh coriander and served with buttered pav or paratha.',
         'tags': ['Non-Veg', 'Egg', 'Quick Bites'], 'calories': '250 kcal', 'prep_time': '10 min'},
    37: {'id': 37, 'category': 'Non-Veg Specials',  'restaurant': 'Tandoor Tales',
         'name': 'Lamb Chops',        'price': 380,
         'image': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=600&q=80',
         'desc': 'Rack of lamb chops marinated with Indian spices and grilled to perfection.',
         'details': 'French-trimmed lamb chops marinated in yoghurt, Kashmiri chilli, cardamom and saffron, then grilled on a charcoal flame until the bone tips are charred and the meat is rosy-pink inside.',
         'tags': ['Non-Veg', 'Grill', 'Premium'], 'calories': '560 kcal', 'prep_time': '40 min'},

    # ── Sweets & Desserts ──────────────────────────────────────────────────
    9:  {'id': 9,  'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Gulab Jamun',       'price': 100,
         'image': 'https://images.unsplash.com/photo-1590130049699-f1f7b516d0fc?w=600&q=80',
         'desc': "Khoya dumplings soaked in rose-saffron sugar syrup — India's festive sweet.",
         'details': 'Khoya-based dumplings gently fried until deep golden brown, then immersed in a warm sugar syrup infused with rose water, cardamom and saffron. Best served warm. An iconic Indian dessert.',
         'tags': ['Veg', 'Dessert', 'Indian Sweets'], 'calories': '280 kcal', 'prep_time': '30 min'},
    20: {'id': 20, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Rasgulla',          'price': 80,
         'image': 'https://images.unsplash.com/photo-1666819904428-b20f2c2d0a82?w=600&q=80',
         'desc': 'Spongy chenna balls poached in light sugar syrup — a Bengali icon.',
         'details': 'Freshly made chenna kneaded smooth, shaped into soft balls and poached in a light sugar syrup until they double in size and become spongy and syrup-soaked. Serve chilled for best results.',
         'tags': ['Veg', 'Dessert', 'Bengali Sweets'], 'calories': '190 kcal', 'prep_time': '35 min'},
    38: {'id': 38, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Kheer',             'price': 90,
         'image': 'https://images.unsplash.com/photo-1666819904428-b20f2c2d0a82?w=600&q=80',
         'desc': 'Creamy slow-cooked rice pudding with cardamom, saffron and pistachios.',
         'details': 'Long-grain rice simmered in full-fat milk for hours until it thickens into a luscious pudding, sweetened with sugar and perfumed with cardamom and saffron. Garnished with silvered pistachios and almonds.',
         'tags': ['Veg', 'Dessert', 'Pudding'], 'calories': '240 kcal', 'prep_time': '40 min'},
    39: {'id': 39, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Gajar Halwa',       'price': 110,
         'image': 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80',
         'desc': 'Slow-cooked grated carrot dessert with ghee, milk, sugar and cardamom.',
         'details': 'Red Delhi carrots freshly grated and cooked low and slow in ghee, then simmered with whole milk until it reduces into a dense, fragrant halwa. Sweetened to taste and topped with cashews and raisins.',
         'tags': ['Veg', 'Dessert', 'Indian Sweets'], 'calories': '300 kcal', 'prep_time': '50 min'},
    40: {'id': 40, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Kulfi Falooda',     'price': 120,
         'image': 'https://images.unsplash.com/photo-1648503552083-c6c03fc33be4?w=600&q=80',
         'desc': 'Dense Indian ice cream with saffron and pistachio on vermicelli and rose syrup.',
         'details': 'Slow-set dense milk kulfi flavoured with saffron and pistachio, sliced over a bed of vermicelli noodles, sweet basil seeds, rose syrup and chilled milk. An old-school Mughal street treat reimagined.',
         'tags': ['Veg', 'Dessert', 'Frozen'], 'calories': '320 kcal', 'prep_time': '5 min'},
    41: {'id': 41, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Jalebi',            'price': 60,
         'image': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80',
         'desc': 'Crispy spiral fritters soaked in warm sugar syrup — a timeless street sweet.',
         'details': 'Fermented batter piped into spirals and deep-fried until crunchy, then immediately dunked into a warm cardamom-saffron sugar syrup. Best eaten hot for that satisfying crunch-then-sweet contrast.',
         'tags': ['Veg', 'Dessert', 'Indian Sweets'], 'calories': '200 kcal', 'prep_time': '20 min'},
    42: {'id': 42, 'category': 'Sweets & Desserts',  'restaurant': 'Sweet Hut',
         'name': 'Rabdi',             'price': 100,
         'image': 'https://images.unsplash.com/photo-1571167530149-c1105da4c2c8?w=600&q=80',
         'desc': 'Thickened sweetened milk with layers of malai, cardamom and nuts.',
         'details': 'Whole milk simmered on low heat for hours, stirred constantly while the cream layers are folded back in repeatedly until it reaches a thick, grainy, intensely flavoured consistency. Served chilled.',
         'tags': ['Veg', 'Dessert', 'Milk Sweets'], 'calories': '270 kcal', 'prep_time': '60 min'},

    # ── Cakes & Bakery ─────────────────────────────────────────────────────
    43: {'id': 43, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Chocolate Truffle Cake','price': 350,
         'image': 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80',
         'desc': 'Moist dark chocolate sponge layered with velvety ganache and truffle crumble.',
         'details': 'Three layers of dense, ultra-moist dark chocolate sponge sandwiched with bittersweet ganache and a crunchy praline crumble. Draped in a mirror-glaze ganache and finished with dark chocolate shards.',
         'tags': ['Veg', 'Cake', 'Chocolate'], 'calories': '480 kcal', 'prep_time': '3 hr'},
    44: {'id': 44, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Red Velvet Cake',   'price': 320,
         'image': 'https://images.unsplash.com/photo-1586788680434-30d324b2d46f?w=600&q=80',
         'desc': 'Velvet-soft red sponge with tangy cream-cheese frosting — a café favourite.',
         'details': 'Buttery red cocoa-tinged sponge layers kept moist with buttermilk, sandwiched and frosted with a tangy, smooth cream-cheese buttercream. Decorated with red velvet crumbs and white chocolate.',
         'tags': ['Veg', 'Cake', 'Bakery'], 'calories': '430 kcal', 'prep_time': '2.5 hr'},
    45: {'id': 45, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Blueberry Cheesecake','price': 290,
         'image': 'https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=600&q=80',
         'desc': 'Baked New-York-style cheesecake with a buttery biscuit base and blueberry compote.',
         'details': 'A classic New York baked cheesecake — dense and creamy, with a buttery digestive biscuit crust. Topped generously with a homemade blueberry compote that cuts perfectly through the richness.',
         'tags': ['Veg', 'Cake', 'Cheesecake'], 'calories': '410 kcal', 'prep_time': '4 hr'},
    46: {'id': 46, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Croissant',         'price': 80,
         'image': 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&q=80',
         'desc': 'Flaky, buttery French croissant with 27 layers of laminated dough.',
         'details': 'Made over two days with cold-proofed European butter, the croissant is rolled and folded into 27 paper-thin layers that puff and separate in the oven into a shatteringly crisp, golden shell with a soft, honeycomb interior.',
         'tags': ['Veg', 'Bakery', 'Pastry'], 'calories': '290 kcal', 'prep_time': '2 days'},
    47: {'id': 47, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Cinnamon Roll',     'price': 90,
         'image': 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&q=80',
         'desc': 'Soft, pillowy rolls swirled with cinnamon-brown sugar, topped with cream cheese glaze.',
         'details': 'Enriched yeast dough rolled with a generous filling of butter, dark brown sugar and fragrant cinnamon, then cut, proofed and baked until golden. Finished with a river of tangy cream-cheese icing while still warm.',
         'tags': ['Veg', 'Bakery', 'Pastry'], 'calories': '380 kcal', 'prep_time': '2.5 hr'},
    48: {'id': 48, 'category': 'Cakes & Bakery',     'restaurant': 'Cake & Co.',
         'name': 'Mango Mousse Cake', 'price': 300,
         'image': 'https://images.unsplash.com/photo-1588195538326-c5b1e9f80a1b?w=600&q=80',
         'desc': "Alphonso mango mousse on a vanilla sponge base — India's summer showstopper.",
         'details': 'A light genoise sponge topped with an airy Alphonso mango mousse, set overnight, and finished with a thin mango jelly glaze and fresh mint. Sweet, tangy and impossibly refreshing.',
         'tags': ['Veg', 'Cake', 'Mousse'], 'calories': '350 kcal', 'prep_time': '5 hr'},

    # ── Drinks & Beverages ─────────────────────────────────────────────────
    49: {'id': 49, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Mango Lassi',       'price': 90,
         'image': 'https://images.unsplash.com/photo-1571748982800-fa51082c2224?w=600&q=80',
         'desc': 'Thick, chilled Alphonso mango blended with creamy yoghurt and a hint of cardamom.',
         'details': "Ripe Alphonso mango pulp blended with thick whole-milk yoghurt, a pinch of cardamom and just enough sugar to balance the fruit's natural tartness. Poured over ice and garnished with a saffron strand.",
         'tags': ['Veg', 'Drink', 'Lassi'], 'calories': '200 kcal', 'prep_time': '5 min'},
    50: {'id': 50, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Masala Chai',       'price': 50,
         'image': 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600&q=80',
         'desc': "Spiced Indian tea with ginger, cardamom and cinnamon — India's comfort drink.",
         'details': 'Strong Assam tea simmered with crushed ginger, cardamom pods, cinnamon, cloves and black pepper, then reduced with whole milk and sweetened with cane sugar. The quintessential Indian ritual in a cup.',
         'tags': ['Veg', 'Drink', 'Tea'], 'calories': '80 kcal', 'prep_time': '5 min'},
    51: {'id': 51, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Rose Sharbat',      'price': 70,
         'image': 'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=600&q=80',
         'desc': 'Chilled rose-flavored drink with basil seeds and crushed ice — a Mughal classic.',
         'details': 'Rose syrup made from real Kannauj petals diluted with chilled water, loaded with bloomed basil seeds (sabja) and poured over crushed ice. Refreshing, floral and visually stunning.',
         'tags': ['Veg', 'Drink', 'Mocktail'], 'calories': '100 kcal', 'prep_time': '5 min'},
    52: {'id': 52, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Cold Coffee',       'price': 120,
         'image': 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=600&q=80',
         'desc': 'Chilled milk blended with strong espresso, ice cream and a drizzle of chocolate.',
         'details': 'Two shots of dark-roast espresso cooled and blended with chilled whole milk, a scoop of vanilla ice cream and a drizzle of Belgian chocolate sauce. Served tall with whipped cream on top.',
         'tags': ['Veg', 'Drink', 'Coffee'], 'calories': '220 kcal', 'prep_time': '5 min'},
    53: {'id': 53, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Fresh Lime Soda',   'price': 60,
         'image': 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&q=80',
         'desc': 'Sparkling soda with freshly squeezed lime, black salt and mint — ultra refreshing.',
         'details': 'Freshly squeezed lime juice, black salt, a pinch of cumin and a splash of sparkling soda water, stirred and served over ice with a sprig of fresh mint. The perfect thirst-quencher on a hot day.',
         'tags': ['Veg', 'Drink', 'Mocktail'], 'calories': '40 kcal', 'prep_time': '2 min'},
    54: {'id': 54, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Thandai',           'price': 100,
         'image': 'https://images.unsplash.com/photo-1625244724120-1fd1d34d00f6?w=600&q=80',
         'desc': 'Chilled milk blended with nuts, seeds and Holi spices — a festive Rajasthani drink.',
         'details': 'A rich, chilled beverage of almonds, melon seeds, rose petals, fennel, black pepper, cardamom and saffron blended with whole milk and filtered. Traditionally prepared during Holi, this drink is cooling and deeply aromatic.',
         'tags': ['Veg', 'Drink', 'Festive'], 'calories': '180 kcal', 'prep_time': '10 min'},
    55: {'id': 55, 'category': 'Drinks & Beverages', 'restaurant': 'Refreshment Bar',
         'name': 'Tender Coconut',    'price': 80,
         'image': 'https://images.unsplash.com/photo-1603569283847-aa295f0d016a?w=600&q=80',
         'desc': "Fresh tender coconut water served in the shell — nature's best electrolyte drink.",
         'details': 'Young green coconuts, freshly dehusked, served with a straw to sip the naturally sweet, mildly saline water and a spoon to scoop the soft, gel-like malai. Completely natural and supremely refreshing.',
         'tags': ['Veg', 'Drink', 'Natural'], 'calories': '45 kcal', 'prep_time': '2 min'},

    # ── Breakfast ──────────────────────────────────────────────────────────
    3:  {'id': 3,  'category': 'Breakfast',           'restaurant': 'Morning Bites',
         'name': 'Chole Bhature',     'price': 180,
         'image': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&q=80',
         'desc': 'Spiced chickpeas with fluffy deep-fried bhature — the king of Punjabi breakfasts.',
         'details': 'Dried chickpeas slow-cooked in an aromatic masala of onion, tomato, ginger and whole spices, paired with pillowy deep-fried bhaturas and a side of pickled onions and green chilli.',
         'tags': ['Veg', 'Punjabi', 'Breakfast'], 'calories': '550 kcal', 'prep_time': '45 min'},
    10: {'id': 10, 'category': 'Breakfast',           'restaurant': 'Morning Bites',
         'name': 'Naan',              'price': 80,
         'image': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=600&q=80',
         'desc': 'Tandoor-baked leavened flatbread — the perfect carrier for any curry.',
         'details': 'Leavened dough of flour, yoghurt and a touch of sugar slapped onto the inner walls of a 400 °C tandoor until blistered and charred in spots. Brushed with butter and garlic fresh out of the oven.',
         'tags': ['Veg', 'Bread', 'North Indian'], 'calories': '260 kcal', 'prep_time': '15 min'},
    56: {'id': 56, 'category': 'Breakfast',           'restaurant': 'Morning Bites',
         'name': 'Aloo Paratha',      'price': 90,
         'image': 'https://images.unsplash.com/photo-1701580533893-33cf0c81756f?w=600&q=80',
         'desc': 'Whole-wheat flatbread stuffed with spiced mashed potato, served with butter and pickle.',
         'details': 'Soft whole-wheat dough stuffed with a filling of mashed potato, green chilli, cumin and coriander, then rolled thin and cooked on a griddle with liberal amounts of ghee until golden and crispy on both sides.',
         'tags': ['Veg', 'Breakfast', 'Punjabi'], 'calories': '370 kcal', 'prep_time': '20 min'},
    57: {'id': 57, 'category': 'Breakfast',           'restaurant': 'Morning Bites',
         'name': 'Poha',              'price': 80,
         'image': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&q=80',
         'desc': 'Flattened rice tempered with mustard seeds, curry leaves, onion and peanuts.',
         'details': 'Moistened flattened rice (chivda) tossed in a tadka of mustard seeds, curry leaves, onion, green chilli and turmeric, then garnished with roasted peanuts, fresh coriander and a squeeze of lemon.',
         'tags': ['Veg', 'Breakfast', 'Maharashtrian'], 'calories': '210 kcal', 'prep_time': '10 min'},
    58: {'id': 58, 'category': 'Breakfast',           'restaurant': 'Morning Bites',
         'name': 'Upma',              'price': 80,
         'image': 'https://images.unsplash.com/photo-1723557082257-4ec81527d40d?w=600&q=80',
         'desc': 'Semolina cooked with vegetables, mustard seeds and curry leaves.',
         'details': 'Roasted semolina (sooji) cooked to a soft, pilaf-like consistency with onion, tomato, green peas and carrots, tempered with mustard seeds, urad dal, curry leaves and fresh coconut. Simple and sustaining.',
         'tags': ['Veg', 'Breakfast', 'South Indian'], 'calories': '190 kcal', 'prep_time': '15 min'},

    # ── Fast Food & Chinese ────────────────────────────────────────────────
    59: {'id': 59, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'Paneer Manchurian', 'price': 180,
         'image': 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=600&q=80',
         'desc': 'Crispy fried paneer tossed in a tangy Indo-Chinese Manchurian sauce.',
         'details': 'Paneer cubes coated in a spiced cornflour batter, fried until crunchy and tossed in a soy-garlic-chilli Manchurian sauce with spring onions. The perfect Indo-Chinese fusion dish.',
         'tags': ['Veg', 'Indo-Chinese', 'Starter'], 'calories': '340 kcal', 'prep_time': '20 min'},
    60: {'id': 60, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'Hakka Noodles',     'price': 160,
         'image': 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&q=80',
         'desc': 'Wok-tossed noodles with vegetables in dark soy sauce — an Indian takeaway staple.',
         'details': 'Boiled Hakka noodles tossed at high heat in a smoking wok with julienned cabbage, carrots, capsicum, soy sauce, vinegar and chilli oil. Ready in minutes and utterly addictive.',
         'tags': ['Veg', 'Noodles', 'Indo-Chinese'], 'calories': '360 kcal', 'prep_time': '15 min'},
    61: {'id': 61, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'Chilli Chicken',    'price': 200,
         'image': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600&q=80',
         'desc': 'Crispy chicken tossed in a spicy soy-chilli sauce with onion and capsicum.',
         'details': 'Boneless chicken pieces marinated in soy and cornflour, fried golden, then tossed with diced onion, green capsicum and a fiery sauce of soy, red chilli paste, vinegar and sesame. A Kolkata street classic.',
         'tags': ['Non-Veg', 'Indo-Chinese', 'Starter'], 'calories': '410 kcal', 'prep_time': '25 min'},
    62: {'id': 62, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'Veg Burger',        'price': 120,
         'image': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80',
         'desc': 'Crispy aloo tikki patty in a sesame bun with lettuce, cheese and sauces.',
         'details': 'A spiced potato-and-pea patty coated in breadcrumbs and fried until golden, placed in a toasted sesame bun with shredded lettuce, sliced tomato, processed cheese and a swirl of mayo and ketchup.',
         'tags': ['Veg', 'Burger', 'Fast Food'], 'calories': '390 kcal', 'prep_time': '15 min'},
    63: {'id': 63, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'Chicken Momos',     'price': 140,
         'image': 'https://images.unsplash.com/photo-1642501776290-4a50e03d4490?w=600&q=80',
         'desc': 'Steamed Himalayan dumplings stuffed with minced chicken and served with fiery chutney.',
         'details': 'Thin rice-flour wrappers pleated around a filling of minced chicken, spring onion, ginger and soy, then steamed to silky perfection. Served with a smoky red chutney of dried chilli, tomato and garlic.',
         'tags': ['Non-Veg', 'Dim Sum', 'Nepali'], 'calories': '280 kcal', 'prep_time': '20 min'},
    64: {'id': 64, 'category': 'Fast Food & Chinese', 'restaurant': 'Dragon Kitchen',
         'name': 'French Fries',      'price': 80,
         'image': 'https://images.unsplash.com/photo-1576107232684-1279f390859f?w=600&q=80',
         'desc': 'Double-fried golden potato strips seasoned with chilli and chaat masala.',
         'details': 'Thick-cut Russet potatoes blanched, chilled, and then double-fried in hot oil for a crispy exterior and fluffy interior. Tossed immediately in a blend of chilli flakes, chaat masala and a pinch of black salt.',
         'tags': ['Veg', 'Fast Food', 'Snack'], 'calories': '300 kcal', 'prep_time': '15 min'},
}


# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/')
def index():
    from app import _food_photo  # import from app to share the same Pexels cache dict
    categories = [
        ('Pizza', 'fa-pizza-slice'), ('Burger', 'fa-burger'), ('Biryani', 'fa-bowl-rice'),
        ('Chinese', 'fa-bowl-food'), ('Momos', 'fa-utensils'), ('South Indian', 'fa-leaf'),
        ('North Indian', 'fa-pepper-hot'), ('Desserts', 'fa-ice-cream'), ('Beverages', 'fa-mug-hot'),
        ('Sandwiches', 'fa-bread-slice'), ('Rolls', 'fa-scroll'), ('Pasta', 'fa-utensils'),
        ('Ice Cream', 'fa-snowflake'), ('Healthy Food', 'fa-seedling'), ('Fast Food', 'fa-bolt'),
        ('Street Food', 'fa-hotdog'), ('Coffee', 'fa-coffee'), ('Bakery', 'fa-cookie-bite'),
        ('Seafood', 'fa-fish'), ('Vegan', 'fa-carrot'),
    ]
    category_cards = [{
        'name': name,
        'icon': icon,
        'image': _food_photo(f'category-{idx}', name.replace(' ', '+'), 480, 360),
        'url': url_for('public.search_page', q=name, type='all'),
    } for idx, (name, icon) in enumerate(categories, 1)]

    top_restaurants = Restaurant.query.filter_by(is_active=True)\
        .order_by(Restaurant.rating.desc(), Restaurant.id.desc()).limit(8).all()
    trending_dishes = FoodItem.query.filter_by(is_available=True)\
        .order_by(FoodItem.is_bestseller.desc(), FoodItem.rating.desc(), FoodItem.id.desc()).limit(10).all()
    latest_blogs = Blog.query.filter_by(status='published')\
        .order_by(Blog.created_at.desc(), Blog.id.desc()).limit(4).all()

    offers = [
        {'title': 'Flat 50% OFF', 'copy': 'On first GrabBite orders above ₹299', 'code': 'WELCOME50',
         'image': _food_photo('offer-1', 'pizza+deal', 1000, 520), 'url': url_for('public.restaurants')},
        {'title': 'Biryani Festival', 'copy': 'Royal dum biryanis from top brands', 'code': 'DUMLOVE',
         'image': _food_photo('offer-2', 'biryani', 1000, 520), 'url': url_for('public.restaurants', q='Biryani')},
        {'title': 'Healthy Week', 'copy': 'Bowls, salads and subs under ₹349', 'code': 'FITBITE',
         'image': _food_photo('offer-3', 'healthy+salad', 1000, 520), 'url': url_for('public.restaurants', q='Healthy Food')},
    ]
    collections = [
        {'title': 'Date Night Picks', 'count': '18 places', 'image': _food_photo('collection-1', 'dinner', 720, 520), 'url': url_for('public.restaurants', sort='rating_desc')},
        {'title': 'Under 30 Minutes', 'count': '24 fast kitchens', 'image': _food_photo('collection-2', 'delivery', 720, 520), 'url': url_for('public.restaurants', sort='delivery_time')},
        {'title': 'Premium Biryani Houses', 'count': '11 royal menus', 'image': _food_photo('collection-3', 'biryani', 720, 520), 'url': url_for('public.restaurants', q='Biryani')},
        {'title': 'Sweet Tooth Trail', 'count': '15 dessert stops', 'image': _food_photo('collection-4', 'dessert', 720, 520), 'url': url_for('public.restaurants', q='Desserts')},
    ]
    best_cuisines = [
        {'name': name, 'url': url_for('public.search_page', q=name, type='all')}
        for name in ['Italian', 'American', 'Mughlai', 'Chinese', 'South Indian', 'Healthy Food', 'Desserts', 'Coffee']
    ]
    reviews = [
        ('Aarav Mehta', 'The new search found KFC, biryani and dessert options instantly. Super polished!', 5),
        ('Nisha Rao', 'Cards feel premium and the offers are easy to scan on mobile.', 5),
        ('Kabir Sethi', 'Loved the collection sliders and fast restaurant discovery.', 4),
        ('Meera Iyer', 'GrabBite makes weekday dinners ridiculously simple.', 5),
        ('Rohan Kapoor', 'The dish cards with veg labels and delivery time are very helpful.', 4),
        ('Fatima Khan', 'Best biryani selection I have seen in one place.', 5),
        ('Dev Malhotra', 'Smooth animations without feeling heavy.', 5),
        ('Ananya Das', 'The category filters actually take me to relevant food.', 4),
        ('Ishaan Gupta', 'Looks and feels like a modern delivery app now.', 5),
    ]

    return render_template(
        'index.html',
        categories=category_cards,
        top_restaurants=top_restaurants,
        trending_dishes=trending_dishes,
        latest_blogs=latest_blogs,
        offers=offers,
        collections=collections,
        best_cuisines=best_cuisines,
        reviews=reviews,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANTS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/restaurants')
def restaurants():
    search_query = request.args.get('q', '')
    cuisine_type = request.args.get('cuisine', '')
    sort_by      = request.args.get('sort', 'rating_desc')
    page         = request.args.get('page', 1, type=int)
    per_page     = 12

    query = Restaurant.query.filter_by(is_active=True)

    if search_query:
        search = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Restaurant.name.ilike(search),
                Restaurant.location.ilike(search),
                Restaurant.description.ilike(search),
                Restaurant.cuisine_type.ilike(search),
            )
        )

    if cuisine_type:
        terms = [t.strip() for t in cuisine_type.split(',')]
        query = query.filter(db.or_(
            *[Restaurant.cuisine_type.ilike(f'%{t}%') for t in terms]
        ))

    if sort_by == 'rating_asc':
        query = query.order_by(Restaurant.rating.asc())
    elif sort_by == 'delivery_time':
        query = query.order_by(Restaurant.delivery_time.asc())
    elif sort_by == 'min_order':
        query = query.order_by(Restaurant.min_order.asc())
    else:
        query = query.order_by(Restaurant.rating.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    cuisine_types = [c[0] for c in
                     db.session.query(Restaurant.cuisine_type).distinct().all()
                     if c[0]]

    def url_for_other_page(p):
        args = request.args.copy()
        args['page'] = p
        return url_for('public.restaurants', **args)

    return render_template('restaurants.html',
                           restaurants=pagination.items,
                           pagination=pagination,
                           url_for_other_page=url_for_other_page,
                           search_query=search_query,
                           cuisine_types=cuisine_types,
                           active_cuisine=cuisine_type,
                           sort_by=sort_by)


@public_bp.route('/restaurant/<int:restaurant_id>')
def restaurant_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    food_items = FoodItem.query.filter_by(
        restaurant_id=restaurant_id, is_available=True
    ).all()
    reviews = Review.query.filter_by(restaurant_id=restaurant_id)\
        .order_by(Review.created_at.desc()).all()

    is_wishlisted = False
    if current_user.is_authenticated:
        is_wishlisted = Wishlist.query.filter_by(
            user_id=current_user.id, restaurant_id=restaurant_id
        ).first() is not None

    return render_template('restaurant_menu.html',
                           restaurant=restaurant,
                           food_items=food_items,
                           reviews=reviews,
                           is_wishlisted=is_wishlisted)


# ─────────────────────────────────────────────────────────────────────────────
# BLOGS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/blogs')
def blogs():
    category = request.args.get('category')
    q = Blog.query.filter_by(status='published')
    if category:
        q = q.filter_by(category=category)
    blog_list = q.order_by(Blog.created_at.desc()).all()
    return render_template('blogs.html', blogs=blog_list)


@public_bp.route('/blog/<int:blog_id>')
def blog_detail(blog_id):
    blog = Blog.query.get_or_404(blog_id)
    from sqlalchemy import update as _sa_update_blog_views
    db.session.execute(
        _sa_update_blog_views(Blog)
        .where(Blog.id == blog_id)
        .values(views=(Blog.views or 0) + 1)
    )
    db.session.commit()
    db.session.refresh(blog)

    related_blogs = Blog.query.filter(
        Blog.category == blog.category,
        Blog.id != blog_id,
        Blog.status == 'published',
    ).order_by(Blog.created_at.desc()).limit(3).all()

    prev_blog = Blog.query.filter(Blog.id < blog_id, Blog.status == 'published')\
        .order_by(Blog.id.desc()).first()
    next_blog = Blog.query.filter(Blog.id > blog_id, Blog.status == 'published')\
        .order_by(Blog.id.asc()).first()

    return render_template('blog_detail.html',
                           blog=blog,
                           related_blogs=related_blogs,
                           prev_blog=prev_blog,
                           next_blog=next_blog)


# ─────────────────────────────────────────────────────────────────────────────
# GALLERY
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/gallery')
def gallery():
    categories_order = [
        'Curries & Mains', 'Rice & Biryani', 'South Indian', 'Snacks & Street Food',
        'Non-Veg Specials', 'Sweets & Desserts', 'Cakes & Bakery',
        'Drinks & Beverages', 'Breakfast', 'Fast Food & Chinese',
    ]
    cat_icons = {
        'Curries & Mains':      ('fa-fire',          '#e53935'),
        'Rice & Biryani':       ('fa-bowl-rice',     '#f59e0b'),
        'South Indian':         ('fa-leaf',           '#10b981'),
        'Snacks & Street Food': ('fa-hotdog',         '#8b5cf6'),
        'Non-Veg Specials':     ('fa-drumstick-bite', '#ef4444'),
        'Sweets & Desserts':    ('fa-candy-cane',     '#ec4899'),
        'Cakes & Bakery':       ('fa-birthday-cake',  '#6366f1'),
        'Drinks & Beverages':   ('fa-glass-water',    '#0ea5e9'),
        'Breakfast':            ('fa-sun',            '#f97316'),
        'Fast Food & Chinese':  ('fa-burger',         '#14b8a6'),
    }
    grouped = OrderedDict()
    for cat in categories_order:
        icon, color = cat_icons.get(cat, ('fa-utensils', '#e53935'))
        dishes_in_cat = [d for d in _DISHES.values() if d.get('category') == cat]
        grouped[cat] = {'icon': icon, 'color': color, 'dishes': dishes_in_cat}

    total = len(_DISHES)
    return render_template('gallery.html', grouped=grouped, total=total)


@public_bp.route('/dish/<int:dish_id>')
def dish_detail(dish_id):
    dish = _DISHES.get(dish_id)
    if not dish:
        abort(404)
    same_cat = [d for d in _DISHES.values() if d['id'] != dish_id and d.get('category') == dish.get('category')]
    others   = [d for d in _DISHES.values() if d['id'] != dish_id and d.get('category') != dish.get('category')]
    related  = (same_cat + others)[:4]
    return render_template('dish_detail.html', dish=dish, related=related)


# ─────────────────────────────────────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/about')
def about():
    return render_template('about.html')


@public_bp.route('/careers')
def careers():
    return render_template('careers.html')


@public_bp.route('/help')
def help():
    return render_template('help.html')


@public_bp.route('/search')
def search_page():
    query       = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    return render_template('search.html', query=query, search_type=search_type)


# ─────────────────────────────────────────────────────────────────────────────
# OFFERS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/offer/<int:offer_id>')
def offer_details(offer_id):
    offer = _static_offers.get(offer_id)
    if not offer:
        abort(404)
    return render_template('offer_details.html', offer=offer)


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST PAGE (user-facing, not the API)
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id)\
        .join(Restaurant, Wishlist.restaurant_id == Restaurant.id).all()
    return render_template('wishlist.html', wishlist_items=items)


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS PAGE
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/notifications')
@login_required
def notifications_page():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(100).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)
