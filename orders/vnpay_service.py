import hashlib
import hmac
import urllib.parse
from django.conf import settings
from django.urls import reverse
from .models import Payment


class VNPayService:
    """Service xử lý thanh toán VNPay"""
    
    def __init__(self):
        self.vnpay_payment_url = getattr(settings, 'VNPAY_PAYMENT_URL', "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
        self.vnpay_return_url = getattr(settings, 'SITE_URL', 'http://localhost:8000') + reverse('orders:vnpay_return')
        self.vnpay_api_url = getattr(settings, 'VNPAY_API_URL', "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction")
        
        # Cấu hình VNPay
        self.vnpay_tmn_code = getattr(settings, 'VNPAY_TMN_CODE', '4JIJFKB8')
        self.vnpay_hash_secret = getattr(settings, 'VNPAY_HASH_SECRET', 'J43Z0GY6CQPS5QYSM3PZ47KX4Q5CNKAD')
        
    def create_payment_url(self, payment: Payment, request):
        """Tạo URL thanh toán VNPay"""
        order = payment.order
        
        # Thông tin giao dịch
        order_id = f"{order.id}_{payment.id}"
        amount = int(payment.amount)  # VNPay yêu cầu số nguyên
        
        # Tham số thanh toán - Đúng format VNPAY
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.vnpay_tmn_code,
            'vnp_Amount': amount * 100,  # VNPay yêu cầu nhân với 100
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': order_id,
            'vnp_OrderInfo': f'Thanh toan don hang {order.id}',
            'vnp_OrderType': 'billpayment',
            'vnp_Locale': 'vn',
            'vnp_ReturnUrl': self.vnpay_return_url,
            'vnp_IpAddr': self.get_client_ip(request),
            'vnp_CreateDate': payment.created_at.strftime('%Y%m%d%H%M%S'),
        }
        
        # Thêm thông tin khách hàng nếu có
        if hasattr(order.user, 'profile'):
            profile = order.user.profile
            if profile.phone:
                vnp_params['vnp_Bill_Mobile'] = profile.phone
            if order.address:
                vnp_params['vnp_Bill_Address'] = order.address
        
        sorted_params = sorted(vnp_params.items())
        
        # 2. Tạo hash_data (Sử dụng urllib.parse.quote_plus cho cả KEY và VALUE)
        # VNPay yêu cầu chuỗi hash phải được encode giống như query string nhưng không có vnp_SecureHash
        hash_data = urllib.parse.urlencode(sorted_params)
        
        # 3. Tạo SecureHash
        vnp_secure_hash = hmac.new(
            self.vnpay_hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # 4. Tạo URL cuối cùng
        # Chú ý: hash_data ở trên đã là một query string chuẩn rồi
        payment_url = f"{self.vnpay_payment_url}?{hash_data}&vnp_SecureHash={vnp_secure_hash}"
        
        # Cập nhật trạng thái payment
        payment.status = 'processing'
        payment.gateway_response = {
            'payment_url': payment_url,
            'vnp_params': vnp_params,
            'hash_data': hash_data,
            'secure_hash': vnp_secure_hash
        }
        payment.save()
        
        return payment_url
    
    def verify_return(self, request):
        """Xác thực phản hồi từ VNPay"""
        vnp_params = {k: v for k, v in request.GET.items() if k.startswith('vnp_')}
        
        # Lấy secure hash từ response
        vnp_secure_hash = vnp_params.pop('vnp_SecureHash', None)
        vnp_secure_hash_type = vnp_params.pop('vnp_SecureHashType', None)
        
        if not vnp_secure_hash:
            return {'success': False, 'message': 'Missing secure hash'}
        
        # Sắp xếp tham số để tạo hash - KHÔNG decode
        sorted_params = sorted(vnp_params.items())
        
        # Tạo hash data - Phải giống hệt như ở create_payment_url
        hash_data = urllib.parse.urlencode(sorted_params)
        
        # Tạo hash để so sánh - dùng HMAC SHA512
        calculated_hash = hmac.new(
            self.vnpay_hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Debug: Log để kiểm tra
        print(f"VNPay Debug:")
        print(f"Received hash: {vnp_secure_hash}")
        print(f"Calculated hash: {calculated_hash}")
        print(f"Hash data: {hash_data}")
        print(f"Secret: {self.vnpay_hash_secret}")
        
        # Kiểm tra hash - so sánh không phân biệt chữ hoa/thường
        if calculated_hash.upper() == vnp_secure_hash.upper():
            # Lấy thông tin giao dịch
            response_code = vnp_params.get('vnp_ResponseCode', '99')
            transaction_status = vnp_params.get('vnp_TransactionStatus', '99')
            txn_ref = vnp_params.get('vnp_TxnRef', '')
            amount = vnp_params.get('vnp_Amount', '0')
            
            # Phân tích order_id và payment_id
            try:
                order_id, payment_id = txn_ref.split('_')
                order_id = int(order_id)
                payment_id = payment_id
            except:
                return {'success': False, 'message': 'Invalid transaction reference'}
            
            # Tìm payment
            try:
                payment = Payment.objects.get(id=payment_id, order__id=order_id)
            except Payment.DoesNotExist:
                return {'success': False, 'message': 'Payment not found'}
            
            # Kiểm tra số tiền
            expected_amount = int(payment.amount) * 100
            if int(amount) != expected_amount:
                return {'success': False, 'message': 'Amount mismatch'}
            
            # Cập nhật trạng thái payment
            if response_code == '00' and transaction_status == '00':
                # Giao dịch thành công
                payment.status = 'completed'
                payment.transaction_id = vnp_params.get('vnp_TransactionNo', '')
                payment.vnpay_transaction_no = vnp_params.get('vnp_TransactionNo', '')
                payment.vnpay_bank_code = vnp_params.get('vnp_BankCode', '')
                payment.vnpay_card_type = vnp_params.get('vnp_CardType', '')
                payment.gateway_response.update(vnp_params)
                payment.save()
                
                # Cập nhật trạng thái đơn hàng nếu đang chờ duyệt
                order = payment.order
                if order.status == 'Pending':
                    order.status = 'Surveying'  # Chuyển sang trạng thái khảo sát
                    order.save()
                
                return {
                    'success': True,
                    'payment': payment,
                    'message': 'Payment successful'
                }
            else:
                # Giao dịch thất bại
                payment.status = 'failed'
                payment.gateway_response.update(vnp_params)
                payment.save()
                
                return {
                    'success': False,
                    'payment': payment,
                    'message': f'Payment failed: {response_code}'
                }
        else:
            return {
                'success': False, 
                'message': 'Invalid secure hash',
                'debug': {
                    'received': vnp_secure_hash,
                    'calculated': calculated_hash,
                    'hash_data': hash_data
                }
            }
    
    def get_client_ip(self, request):
        """Lấy IP address của client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def query_transaction(self, payment: Payment):
        """Truy vấn trạng thái giao dịch từ VNPay API"""
        # Implementation for querying transaction status
        # This would be used for checking payment status periodically
        pass
