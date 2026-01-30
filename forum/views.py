from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q, F
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Post, Comment, Category
from .forms import PostForm, CommentForm

class ForumHomeView(ListView):
    model = Post
    template_name = 'forum/home.html'
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Post.objects.select_related('author', 'category')
        
        # Filter by category
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Search
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(author__username__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        
        # Process post content to anonymize images
        from .utils import process_markdown_with_anonymous_images
        import re
        
        for post in context['posts']:
            # Process content and store both raw and processed versions
            processed_html = process_markdown_with_anonymous_images(post.content)
            post.processed_content = processed_html
            
            # Create a text preview that preserves image count but limits text
            # Extract text content (excluding HTML tags) for preview length calculation
            text_content = re.sub(r'<[^>]+>', '', processed_html)
            if len(text_content) > 200:
                # Find a good cutoff point that doesn't break HTML
                preview_text = text_content[:200] + '...'
                # Count images in the full content
                image_count = len(re.findall(r'<img[^>]+>', processed_html))
                if image_count > 0:
                    if image_count > 1:
                        preview_text += f' ({image_count} images)'
                    else:
                        preview_text += f' ({image_count} image)'
                post.content_preview = preview_text
            else:
                # For short content, show text only (no HTML)
                post.content_preview = text_content
        
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'forum/post_detail.html'
    context_object_name = 'post'
    slug_url_kwarg = 'slug'
    
    def get_object(self):
        post = super().get_object()
        # Update view count
        Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
        return post
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['post']
        # Get comments
        context['comments'] = post.comments.filter(parent=None).select_related('author')
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'forum/post_form.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Đã tạo bài viết thành công!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thêm bài đăng'
        return context

class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'forum/post_form.html'
    slug_url_kwarg = 'slug'
    
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user and not request.user.has_perm('forum.manage_post'):
            return HttpResponseForbidden("Bạn không có quyền chỉnh sửa bài viết này.")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.updated_at = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, 'Đã cập nhật bài viết thành công!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Chỉnh sửa bài viết'
        return context

class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'forum/post_confirm_delete.html'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('forum:home')
    
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user and not request.user.has_perm('forum.manage_post'):
            return HttpResponseForbidden("Bạn không có quyền xóa bài viết này.")
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Đã xóa bài viết thành công!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    if post.is_locked and not request.user.has_perm('forum.manage_post'):
        messages.error(request, 'Bài viết này đã bị khóa.')
        return redirect('forum:post_detail', slug=slug)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            
            # Handle reply
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)
            
            comment.save()
            messages.success(request, 'Đã thêm bình luận thành công!')
            return redirect('forum:post_detail', slug=post.slug)
    else:
        form = CommentForm()
    
    return render(request, 'forum/add_comment.html', {
        'form': form,
        'post': post,
        'parent_id': request.GET.get('parent_id')
    })

# Admin Functions
@permission_required('forum.pin_post', raise_exception=True)
def pin_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    post.is_pinned = not post.is_pinned
    post.save()
    
    message = f"Đã {'ghim' if post.is_pinned else 'bỏ ghim'} bài viết thành công!"
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'is_pinned': post.is_pinned
        })
    
    messages.success(request, message)
    return redirect('forum:post_detail', slug=slug)

@permission_required('forum.manage_post', raise_exception=True)
def lock_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    post.is_locked = not post.is_locked
    post.save()
    
    message = f"Đã {'khóa' if post.is_locked else 'mở khóa'} bài viết thành công!"
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'is_locked': post.is_locked
        })
    
    messages.success(request, message)
    return redirect('forum:post_detail', slug=slug)

@permission_required('forum.manage_post', raise_exception=True)
def delete_post_ajax(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    if request.method == 'POST':
        post_title = post.title
        post.delete()
        
        message = f"Đã xóa bài viết '{post_title}' thành công!"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message
            })
        
        messages.success(request, message)
        return redirect('forum:manage_posts')
    
    return JsonResponse({'success': False, 'message': 'Phương thức yêu cầu không hợp lệ'})

@permission_required("forum.manage_post", raise_exception=True)
def manage_posts(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'forum/manage_posts.html', {'posts': posts})

@permission_required("forum.manage_comment", raise_exception=True)
def manage_comments(request):
    comments = Comment.objects.all().order_by('-created_at')
    return render(request, 'forum/manage_comments.html', {'comments': comments})
