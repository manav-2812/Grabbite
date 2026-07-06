"""
Grabbite — API: Address
/api/address/add, /api/address/<id> (DELETE)
"""
from flask import request, jsonify
from flask_login import current_user, login_required

from db import db
from models import Address
from blueprints.api import api_bp


@api_bp.route('/api/address/add', methods=['POST'])
@login_required
def api_address_add():
    data = request.get_json() or {}
    try:
        if data.get('is_default'):
            Address.query.filter_by(user_id=current_user.id, is_default=True)\
                .update({'is_default': False})

        addr = Address(
            user_id=current_user.id,
            label=data.get('label', 'Home'),
            full_address=data.get('full_address', ''),
            city=data.get('city'),
            state=data.get('state'),
            pincode=data.get('pincode'),
            landmark=data.get('landmark'),
            is_default=bool(data.get('is_default', False)),
        )
        db.session.add(addr)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Address saved', 'id': addr.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/address/<int:address_id>', methods=['DELETE'])
@login_required
def api_address_delete(address_id):
    addr = Address.query.filter_by(id=address_id, user_id=current_user.id).first()
    if not addr:
        return jsonify({'success': False, 'message': 'Address not found'}), 404
    db.session.delete(addr)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Address deleted'})
