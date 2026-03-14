# DTHub - IoT & Microcontroller Platform

DTHub là nền tảng thương mại điện tử chuyên về các sản phẩm IoT, Microcontroller và dịch vụ lắp đặt liên quan.

## 🚀 Quick Start

### 1. Clone và cài đặt
```bash
git clone <repository-url>
cd dthub
pip install -r requirements.txt
```

### 2. Cấu hình môi trường
```bash
# Tạo file .env
touch .env

# Thêm nội dung sau vào file .env:
```

**File .env Configuration:**
```env

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# VNPay Configuration (Sandbox/Test Environment)
VNPAY_TMN_CODE=4JIJFKB8
VNPAY_HASH_SECRET=J43Z0GY6CQPS5QYSM3PZ47KX4Q5CNKAD
VNPAY_PAYMENT_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_API_URL=https://sandbox.vnpayment.vn/merchant_webapi/api/transaction

# Site Configuration
SITE_URL=http://localhost:8000
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# For development with ngrok:
# SITE_URL=https://your-domain.ngrok.io
# CSRF_TRUSTED_ORIGINS=https://your-domain.ngrok.io

# For production:
# DEBUG=False
# SITE_URL=https://yourdomain.com
# CSRF_TRUSTED_ORIGINS=https://yourdomain.com
# VNPAY_PAYMENT_URL=https://vnpayment.vn/paymentv2/vpcpay.html
# VNPAY_API_URL=https://vnpayment.vn/merchant_webapi/api/transaction
```

### 3. Database migration
```bash
python manage.py migrate
```

### 4. Tạo superuser
```bash
python manage.py createsuperuser
```

### 5. Khởi động server
```bash
python manage.py runserver
```

## 🔧 Cấu hình Thanh toán VNPay

### Thông tin test VNPay
- **Terminal ID**: `4JIJFKB8`
- **Secret Key**: `J43Z0GY6CQPS5QYSM3PZ47KX4Q5CNKAD`
- **Thẻ test**: NCB `9704198526191432198` / OTP `123456`

### URLs quan trọng
- **Merchant Admin**: https://sandbox.vnpayment.vn/merchantv2/
  - Username: ducdz1m2@gmail.com
  - Password: (mật khẩu đã đăng ký)
- **Test Case IPN**: https://sandbox.vnpayment.vn/vnpaygw-sit-testing/user/login
- **Tài liệu**: https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html
- **Code demo**: https://sandbox.vnpayment.vn/apis/vnpay-demo/code-demo-tích-hợp

### Payment Flow
1. Customer chọn sản phẩm → Đặt hàng
2. Chọn phương thức thanh toán (VNPay/COD)
3. VNPay: Chuyển hướng → Thanh toán → Callback verification
4. COD: Xác nhận đơn → Giao hàng → Thu tiền khi nhận hàng
5. Update trạng thái đơn hàng và gửi thông báo

## 📱 Features

### 🛒 E-commerce
- Quản lý sản phẩm IoT/Microcontroller
- Giỏ hàng và checkout
- Thanh toán VNPay + COD
- Quản lý đơn hàng

### 👥 User Management
- Đăng ký/Đăng nhập
- Profile người dùng
- Phân quyền customer/staff/admin

### 💬 Chat & Support
- Real-time chat với Django Channels
- Hệ thống support ticket
- AI Hub integration

### 📊 Dashboard
- Analytics cho admin
- Tech dashboard cho kỹ thuật viên
- Customer order tracking

## 🏗️ Architecture

### Apps Structure
```
dthub/
├── accounts/          # User management
├── products/          # Product catalog
├── orders/           # Order & payment processing
├── ai_hub/           # AI services
├── chat/             # Real-time chat
├── support/          # Support tickets
├── firmware/         # Firmware management
└── dashboard/        # Admin dashboards
```

### Payment Flow
1. Customer chọn sản phẩm → Đặt hàng
2. Chọn phương thức thanh toán (VNPay/COD)
3. VNPay: Chuyển hướng → Thanh toán → Callback
4. COD: Xác nhận đơn → Giao hàng → Thu tiền
5. Update trạng thái đơn hàng

## 🛠️ Development

### Requirements
- Python 3.8+
- Django 6.0
- SQLite (development) / PostgreSQL (production)

### Key Dependencies
```txt
Django==6.0
django-allauth==65.13.1
channels==4.3.2
redis==7.1.0
Pillow==12.1.0
django-vnpay==1.0.0
```

### Environment Variables
```env
# Required
SECRET_KEY=your-secret-key
DEBUG=True

# VNPay (Required for payment)
VNPAY_TMN_CODE=4JIJFKB8
VNPAY_HASH_SECRET=J43Z0GY6CQPS5QYSM3PZ47KX4Q5CNKAD

# Site Configuration
SITE_URL=http://localhost:8000
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

## 🚀 Deployment

### Production Setup
1. **Environment Variables**:
```env
DEBUG=False
SECRET_KEY=your-production-secret
SITE_URL=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# VNPay Production
VNPAY_PAYMENT_URL=https://vnpayment.vn/paymentv2/vpcpay.html
VNPAY_API_URL=https://vnpayment.vn/merchant_webapi/api/transaction
```

2. **Database**: PostgreSQL recommended
3. **Static files**: AWS S3 hoặc similar
4. **Web server**: Nginx + Gunicorn
5. **WebSocket**: Daphne for Django Channels

### IPN Configuration
Cung cấp URL cho VNPay: `https://yourdomain.com/orders/vnpay/ipn/`

## 🐛 Troubleshooting

### Common Issues

#### CSRF Error (403)
```python
# Add to ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
ALLOWED_HOSTS = ['yourdomain.com']
CSRF_TRUSTED_ORIGINS = ['https://yourdomain.com']
```

#### Invalid Secure Hash
- ✅ Fixed: Hash data không URL encode khi tạo checksum
- Check console logs cho debug info

#### Payment Callback Issues
- Kiểm tra `SITE_URL` trong .env
- Đảm bảo URL có thể truy cập từ bên ngoài

### Debug Mode
Enable debug logs trong `vnpay_service.py` để kiểm tra:
```
VNPay Debug:
Received hash: [hash từ VNPay]
Calculated hash: [hash tính toán]
Hash data: [dữ liệu dùng tạo hash]
```

## 📞 Support

### Documentation
- **VNPay Integration**: Xem section cấu hình VNPay
- **API Documentation**: `/admin/docs/` (nếu có)
- **Code Examples**: Xem trong `examples/` directory

### Contact
- **Email**: support@dthub.com
- **Hotline**: 1900-XXXX
- **Documentation**: https://docs.dthub.com

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📋 Changelog

### v1.0.0 (2026-02-03)
- ✅ E-commerce platform với product management
- ✅ VNPay + COD payment integration
- ✅ User authentication & authorization
- ✅ Real-time chat với Django Channels
- ✅ Support ticket system
- ✅ Admin dashboards
- ✅ AI Hub integration
- ✅ Firmware management

### Known Issues
- Template currency filters conflict (warning only)
- WebSocket connection stability (in development)

---

**Built with ❤️ using Django, Channels, and VNPay**
