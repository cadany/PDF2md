from datetime import datetime

# 模拟数据存储 - 在实际应用中，这应该是数据库
bids_data = []
bid_counter = 1

def get_all_bids(sort_by='created_at', order='desc'):
    """获取所有竞价信息"""
    sorted_bids = sorted(bids_data, key=lambda x: x[sort_by], reverse=(order == 'desc'))
    return sorted_bids, len(sorted_bids)

def create_bid(item_name, bid_amount, bidder_name='Anonymous', status='active'):
    """创建新的竞价"""
    global bid_counter
    global bids_data
    
    new_bid = {
        'id': bid_counter,
        'item_name': item_name,
        'bid_amount': bid_amount,
        'bidder_name': bidder_name,
        'created_at': datetime.now().isoformat(),
        'status': status
    }
    
    bids_data.append(new_bid)
    bid_counter += 1
    
    return new_bid

def get_bid_by_id(bid_id):
    """获取特定竞价信息"""
    bid = next((bid for bid in bids_data if bid['id'] == bid_id), None)
    return bid

def update_bid(bid_id, data):
    """更新特定竞价信息"""
    global bids_data
    
    # 找到要更新的竞价
    bid_index = next((i for i, bid in enumerate(bids_data) if bid['id'] == bid_id), None)
    
    if bid_index is None:
        return None
    
    # 更新允许的字段
    updatable_fields = ['item_name', 'bid_amount', 'bidder_name', 'status']
    for field in updatable_fields:
        if field in data:
            if field == 'bid_amount':
                bids_data[bid_index][field] = float(data[field])
            else:
                bids_data[bid_index][field] = data[field]
    
    return bids_data[bid_index]

def delete_bid(bid_id):
    """删除特定竞价"""
    global bids_data
    bid = next((bid for bid in bids_data if bid['id'] == bid_id), None)
    
    if not bid:
        return False
    
    bids_data = [bid for bid in bids_data if bid['id'] != bid_id]
    return True

def get_bid_analysis():
    """获取竞价分析"""
    if not bids_data:
        return None
    
    total_bids = len(bids_data)
    total_amount = sum(bid['bid_amount'] for bid in bids_data)
    avg_amount = total_amount / total_bids if total_bids > 0 else 0
    
    # 找出最高和最低竞价
    highest_bid = max(bids_data, key=lambda x: x['bid_amount'])
    lowest_bid = min(bids_data, key=lambda x: x['bid_amount'])
    
    # 按状态分组
    status_counts = {}
    for bid in bids_data:
        status = bid['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    analysis = {
        'total_bids': total_bids,
        'total_amount': total_amount,
        'average_bid_amount': avg_amount,
        'highest_bid': highest_bid,
        'lowest_bid': lowest_bid,
        'status_distribution': status_counts
    }
    
    return analysis

def clear_bids():
    """清空所有竞价数据"""
    global bids_data, bid_counter
    bids_data = []
    bid_counter = 1