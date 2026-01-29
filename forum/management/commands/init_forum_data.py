from django.core.management.base import BaseCommand
from django.utils.text import slugify
from forum.models import Category

class Command(BaseCommand):
    help = 'Create initial forum categories and tags'

    def handle(self, *args, **options):
        # Create forum categories
        categories = [
            {
                'name': 'Vi điều khiển',
                'slug': 'vi-dieu-khien',
                'description': 'Thảo luận về ESP32, STM32, Arduino và các vi điều khiển khác',
                'icon': 'fas fa-microchip',
                'order': 1
            },
            {
                'name': 'Cảm biến & Thiết bị',
                'slug': 'cam-bien-thiet-bi',
                'description': 'Cảm biến nhiệt độ, cảm biến chuyển động, động cơ và các linh kiện khác',
                'icon': 'fas fa-thermometer-half',
                'order': 2
            },
            {
                'name': 'Truyền thông không dây',
                'slug': 'truyen-thong-khong-day',
                'description': 'WiFi, Bluetooth, LoRa, Zigbee và các giao thức không dây khác',
                'icon': 'fas fa-wifi',
                'order': 3
            },
            {
                'name': 'Quản lý nguồn',
                'slug': 'quan-ly-nguon',
                'description': 'Nguồn điện, pin, bộ điều áp và quản lý năng lượng',
                'icon': 'fas fa-battery-full',
                'order': 4
            },
            {
                'name': 'Lập trình & Phần mềm',
                'slug': 'lap-trinh-phan-mem',
                'description': 'C/C++, MicroPython, Arduino IDE và các công cụ phát triển',
                'icon': 'fas fa-code',
                'order': 5
            },
            {
                'name': 'Dự án & Hướng dẫn',
                'slug': 'du-an-huong-dan',
                'description': 'Chia sẻ dự án và học hỏi từ các hướng dẫn',
                'icon': 'fas fa-project-diagram',
                'order': 6
            },
            {
                'name': 'Chợ điện tử',
                'slug': 'cho-dien-tu',
                'description': 'Mua, bán và trao đổi linh kiện điện tử',
                'icon': 'fas fa-shopping-cart',
                'order': 7
            }
        ]

        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Initial forum categories created successfully!')
        )
