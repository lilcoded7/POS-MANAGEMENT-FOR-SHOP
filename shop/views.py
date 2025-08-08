from django.shortcuts import render
from shop.models.products import Product, Category
from shop.models.orders import Order
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shop.models.order_items import OrderItem
import json
# Create your views here.


def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()

    if 'category' in request.GET:
        category = request.GET.get('category')
        if category and category !='All Product':
            products = products.filter(category__name=category)

        products_data = [
            {
                'name':product.name,
                'selling_price':product.selling_price,
                'stock_quantity':product.stock_quantity,
                'status':product.status,
                'category':product.category.name if product.category else ''
            } for product in products
        ]
        return JsonResponse({'products':products_data})
    
    if request.method == 'POST':
        product_name = request.POST['name']

        products = Product.objects.filter(name__icontains=product_name)


    context = {
        'products':products,
        'categories':categories,
        'orders':orders
    }
    return render(request, 'main/home.html', context)





@csrf_exempt
def add_to_order(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        
        order, created = Order.objects.get_or_create(
            status='pending',
            defaults={'total_price': 0}
        )
        
        order_item, created = OrderItem.objects.get_or_create(
            order=order,
            product=product,
            defaults={'quantity': 1}
        )
        
        if not created:
            order_item.quantity += 1
            order_item.save()
        
        return JsonResponse({
            'success': True,
            'order_items': get_order_items_data(order)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
def update_order_item(request, item_id):
    try:
        data = json.loads(request.body)
        change = data.get('change', 0)
        
        order_item = OrderItem.objects.get(id=item_id)
        order_item.quantity += change
        
        if order_item.quantity <= 0:
            order_item.delete()
        else:
            order_item.save()
        
        return JsonResponse({
            'success': True,
            'order_items': get_order_items_data(order_item.order)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
def complete_order(request):
    try:
   
        order = Order.objects.filter(status='pending').first()
        
        if not order or not order.items.exists():
            raise Exception('No active order to complete')
        
        order.status = 'success'
        order.total_price = order.get_total_price()
        order.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def get_active_order(request):
    try:
        order = Order.objects.filter(status='pending').first()
        if order:
            return JsonResponse({
                'success': True,
                'order_items': get_order_items_data(order)
            })
        return JsonResponse({'success': True, 'order_items': []})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def get_recent_orders(request):
    try:
        orders = Order.objects.filter(status='success').order_by('-created_at')[:8]
        orders_data = [{
            'id': order.id,
            'order_id': order.order_id,
            'total_price': float(order.total_price),
            'status': order.status,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'item_count': order.items.count()
        } for order in orders]
        
        return JsonResponse({
            'success': True,
            'orders': orders_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def get_order_items_data(order):
    return [
        {
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'product_price': float(item.product.selling_price),
            'quantity': item.quantity
        }
        for item in order.items.all()
    ]