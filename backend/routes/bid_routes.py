from flask import Blueprint, jsonify, request
from security import security_check, validate_input_types, csrf_protect
from service.bid_service import (
    get_all_bids,
    create_bid,
    get_bid_by_id,
    update_bid,
    delete_bid,
    get_bid_analysis,
    clear_bids
)

# 创建bid蓝图
bid_bp = Blueprint('bid_bp', __name__)

@bid_bp.route('/', methods=['GET'])
@security_check
@csrf_protect
def home():
    return jsonify({
        'message': 'Welcome to BiddingChecker API',
        'status': 'running',
        'endpoints': {
            'get_bids': 'GET /api/bids',
            'create_bid': 'POST /api/bids',
            'get_bid': 'GET /api/bids/<id>',
            'update_bid': 'PUT /api/bids/<id>',
            'delete_bid': 'DELETE /api/bids/<id>',
            'get_bid_analysis': 'GET /api/bids/analysis',
            'clear_bids': 'POST /api/bids/clear',
            'analyze_pdf': 'POST /api/pdf/analyze (file upload with page_num)'
        }
    })

@bid_bp.route('/api/bids', methods=['GET'])
@security_check
def get_bids():
    """获取所有竞价信息"""
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    
    # 验证参数类型
    if sort_by and not isinstance(sort_by, str):
        return jsonify({'error': 'Invalid sort parameter'}), 400
    if order and not isinstance(order, str):
        return jsonify({'error': 'Invalid order parameter'}), 400
    
    bids, count = get_all_bids(sort_by, order)
    
    return jsonify({
        'bids': bids,
        'count': count
    })

@bid_bp.route('/api/bids', methods=['POST'])
@security_check
@csrf_protect
def create_bid_endpoint():
    """创建新的竞价"""
    data = request.get_json()
    
    if not data or 'item_name' not in data or 'bid_amount' not in data:
        return jsonify({'error': 'Missing required fields: item_name, bid_amount'}), 400
    
    # 验证输入类型
    is_valid, error_msg = validate_input_types(data, {
        'bid_amount': (int, float),
        'bidder_name': str,
        'status': str
    })
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # 验证数据合理性
    if not isinstance(data['item_name'], str) or len(data['item_name']) > 255:
        return jsonify({'error': 'Invalid item_name'}), 400
    
    try:
        bid_amount = float(data['bid_amount'])
        if bid_amount <= 0:
            return jsonify({'error': 'Bid amount must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid bid_amount'}), 400
    
    if 'bidder_name' in data and (not isinstance(data['bidder_name'], str) or len(data['bidder_name']) > 100):
        return jsonify({'error': 'Invalid bidder_name'}), 400
    
    if 'status' in data and data['status'] not in ['active', 'inactive', 'won', 'lost']:
        return jsonify({'error': 'Invalid status'}), 400
    
    new_bid = create_bid(
        item_name=data['item_name'],
        bid_amount=bid_amount,
        bidder_name=data.get('bidder_name', 'Anonymous'),
        status=data.get('status', 'active')
    )
    
    return jsonify({
        'message': 'Bid created successfully',
        'bid': new_bid
    }), 201

@bid_bp.route('/api/bids/<int:bid_id>', methods=['GET'])
@security_check
def get_bid_endpoint(bid_id):
    """获取特定竞价信息"""
    # 验证bid_id合理性
    if bid_id <= 0:
        return jsonify({'error': 'Invalid bid ID'}), 400
    
    bid = get_bid_by_id(bid_id)
    
    if not bid:
        return jsonify({'error': 'Bid not found'}), 404
    
    return jsonify({'bid': bid})

@bid_bp.route('/api/bids/<int:bid_id>', methods=['PUT'])
@security_check
@csrf_protect
def update_bid_endpoint(bid_id):
    """更新特定竞价信息"""
    # 验证bid_id合理性
    if bid_id <= 0:
        return jsonify({'error': 'Invalid bid ID'}), 400
    
    bid = get_bid_by_id(bid_id)
    
    if not bid:
        return jsonify({'error': 'Bid not found'}), 404
    
    data = request.get_json()
    
    if data:
        # 验证输入类型
        is_valid, error_msg = validate_input_types(data, {
            'bid_amount': (int, float),
            'bidder_name': str,
            'status': str,
            'item_name': str
        })
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # 验证数据合理性
        if 'item_name' in data and (not isinstance(data['item_name'], str) or len(data['item_name']) > 255):
            return jsonify({'error': 'Invalid item_name'}), 400
        
        if 'bid_amount' in data:
            try:
                bid_amount = float(data['bid_amount'])
                if bid_amount <= 0:
                    return jsonify({'error': 'Bid amount must be positive'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid bid_amount'}), 400
        
        if 'bidder_name' in data and (not isinstance(data['bidder_name'], str) or len(data['bidder_name']) > 100):
            return jsonify({'error': 'Invalid bidder_name'}), 400
        
        if 'status' in data and data['status'] not in ['active', 'inactive', 'won', 'lost']:
            return jsonify({'error': 'Invalid status'}), 400
    
    updated_bid = update_bid(bid_id, data)
    
    return jsonify({
        'message': 'Bid updated successfully',
        'bid': updated_bid
    })

@bid_bp.route('/api/bids/<int:bid_id>', methods=['DELETE'])
@security_check
@csrf_protect
def delete_bid_endpoint(bid_id):
    """删除特定竞价"""
    # 验证bid_id合理性
    if bid_id <= 0:
        return jsonify({'error': 'Invalid bid ID'}), 400
    
    success = delete_bid(bid_id)
    
    if not success:
        return jsonify({'error': 'Bid not found'}), 404
    
    return jsonify({'message': f'Bid {bid_id} deleted successfully'})

@bid_bp.route('/api/bids/analysis', methods=['GET'])
@security_check
def get_bid_analysis_endpoint():
    """获取竞价分析"""
    analysis = get_bid_analysis()
    
    if analysis is None:
        return jsonify({
            'message': 'No bids available for analysis',
            'analysis': {}
        })
    
    return jsonify({
        'analysis': analysis,
        'message': 'Bid analysis generated successfully'
    })

@bid_bp.route('/api/bids/clear', methods=['POST'])
@security_check
@csrf_protect
def clear_bids_endpoint():
    """清空所有竞价数据（仅用于测试）"""
    # 这里可以添加额外的安全检查，比如验证请求来源或添加确认机制
    clear_bids()
    
    return jsonify({'message': 'All bids cleared successfully'})