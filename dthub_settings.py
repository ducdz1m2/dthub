import os

# VNPay Configuration
VNPAY_TMN_CODE = os.getenv('VNPAY_TMN_CODE', '4JIJFKB8')
VNPAY_HASH_SECRET = os.getenv('VNPAY_HASH_SECRET', 'J43Z0GY6CQPS5QYSM3PZ47KX4Q5CNKAD')
VNPAY_PAYMENT_URL = os.getenv('VNPAY_PAYMENT_URL', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
VNPAY_API_URL = os.getenv('VNPAY_API_URL', 'https://sandbox.vnpayment.vn/merchant_webapi/api/transaction')

# Site Configuration
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')

# CSRF Trusted Origins for ngrok
CSRF_TRUSTED_ORIGINS = [os.getenv('CSRF_TRUSTED_ORIGINS')] if os.getenv('CSRF_TRUSTED_ORIGINS') else []
