"""
Grabbite — Shared constants / enum tuples.
"""

ROLES = ('admin', 'customer', 'restaurant_owner', 'delivery_partner')
ORDER_STATUSES = ('cart', 'placed', 'accepted', 'preparing', 'ready',
                  'picked', 'on_the_way', 'delivered', 'cancelled', 'refunded')
PAYMENT_METHODS = ('cod', 'upi', 'card', 'wallet', 'netbanking')
PAYMENT_STATUSES = ('pending', 'paid', 'failed', 'refunded')
