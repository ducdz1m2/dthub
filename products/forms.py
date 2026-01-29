from django import forms
from .models import Product, ProductImage

class ProductForm(forms.ModelForm):
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            # Kiểm tra unique slug, nhưng cho phép giữ nguyên slug của sản phẩm hiện tại
            instance = getattr(self, 'instance', None)
            queryset = Product.objects.filter(slug=slug)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError('Slug này đã tồn tại. Vui lòng chọn slug khác.')
        return slug
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Giá sản phẩm không được âm.')
        return price
    
    class Meta:
        model = Product
        fields = ['name', 'slug', 'product_type', 'price', 'stock', 'is_active', 'datasheet_url', 'description']

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']

ProductImageFormSet = forms.inlineformset_factory(
    Product, ProductImage, form=ProductImageForm,
    extra=3, can_delete=True
)
