from django.shortcuts import render
from products.models import Product, ProductImage
from forum.models import Post, Category
from orders.models import Review
from django.db.models import Avg

def home(request):
    # Get featured products (limit to 6 for homepage)
    products = Product.objects.filter(is_active=True)[:6]
    
    # Get latest posts for blog section
    posts = Post.objects.select_related('author', 'category').order_by('-created_at')[:2]
    
    # Get reviews (since there are no reviews yet, we'll create some sample data)
    reviews = Review.objects.select_related('user', 'order__product').order_by('-created_at')[:4]
    
    # If no reviews exist, create some sample data for display
    if not reviews.exists():
        # Create sample reviews data for display (not saved to database)
        sample_reviews = [
            {
                'user_name': 'Nguyễn Văn Minh',
                'rating': 5,
                'comment': 'Giải pháp IoT triển khai nhanh, thiết bị chạy ổn định. Đội kỹ thuật hỗ trợ rất nhiệt tình và có trách nhiệm.',
                'avatar_url': 'https://i.pravatar.cc/80?img=12'
            },
            {
                'user_name': 'Trần Thị Hạnh', 
                'rating': 4,
                'comment': 'Sản phẩm đúng mô tả, chi phí hợp lý. Mong trong tương lai có thêm nhiều mẫu thiết bị hơn.',
                'avatar_url': 'https://i.pravatar.cc/80?img=32'
            },
            {
                'user_name': 'Lê Quốc Bảo',
                'rating': 5,
                'comment': 'Hệ thống chạy ổn định liên tục, rất phù hợp cho môi trường sản xuất. Đáng tiền.',
                'avatar_url': 'https://i.pravatar.cc/80?img=45'
            },
            {
                'user_name': 'Phạm Hoàng Long',
                'rating': 4,
                'comment': 'Giải pháp dễ mở rộng, tài liệu rõ ràng. Phù hợp cho cả đội kỹ thuật nhỏ.',
                'avatar_url': 'https://i.pravatar.cc/80?img=7'
            }
        ]
    else:
        sample_reviews = []
    
    context = {
        'products': products,
        'posts': posts,
        'reviews': reviews,
        'sample_reviews': sample_reviews,
    }
    
    return render(request, "dashboard/home.html", context)