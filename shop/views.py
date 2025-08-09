from django.shortcuts import render, get_object_or_404, redirect
from shop.models.products import Product, Category
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from shop.models.orders import Order
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shop.models.order_items import OrderItem
from shop.models.cancel_order import CancelOrder
from shop.forms import CancelOrderForm
from shop.models.reports import Report
from django.db.models import Sum
from django.contrib import messages
from datetime import datetime, time, timedelta
from django.utils import timezone
import json

# Create your views here.


def home(request):
    today = timezone.localdate()

    start_datetime = datetime.combine(today, time.min).replace(
        tzinfo=timezone.get_current_timezone()
    )
    end_datetime = datetime.combine(today, time.max).replace(
        tzinfo=timezone.get_current_timezone()
    )

    today_orders = Order.objects.filter(
        status="success",
        is_canceled=False,
        created_at__range=(start_datetime, end_datetime),
    )
    canceled_order = Order.objects.filter(
        is_canceled=True, created_at__range=(start_datetime, end_datetime)
    ).count()

    total_sales = today_orders.aggregate(
        total=Coalesce(Sum("total_price"), 0, output_field=DecimalField())
    )["total"]

    order_count = today_orders.count()

    average_order_value = total_sales / order_count if order_count > 0 else 0

    products = Product.objects.all()
    categories = Category.objects.all()
    orders = Order.objects.all()
    reasons = CancelOrder.objects.all()
    form = CancelOrderForm()

    if "category" in request.GET:
        category = request.GET.get("category")
        if category and category != "All Product":
            products = products.filter(category__name=category)

        products_data = [
            {
                "name": product.name,
                "selling_price": product.selling_price,
                "stock_quantity": product.stock_quantity,
                "status": product.status,
                "category": product.category.name if product.category else "",
            }
            for product in products
        ]
        return JsonResponse({"products": products_data})
    
    order_items = [
        {
            'order':order,
            'order_items':OrderItem.objects.filter(order=order),
        }for order in Order.objects.all()
    ]
  

    if request.method == "POST":
        product_name = request.POST["name"]

        products = Product.objects.filter(name__icontains=product_name)

    context = {
        "products": products,
        "categories": categories,
        'order_items':order_items,
        "orders": orders,
        "reasons": reasons,
        "form": form,
        "total_sales": float(total_sales) or 0.00,
        "order_count": order_count or 0,
        "average_order_value": float(average_order_value) or 0.00,
        "canceled_order": canceled_order or 0,
    }
    return render(request, "main/home.html", context)



def get_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()

    data = [
    {
        'id': item.id,
        'product': item.product.name,
        'quantity': item.quantity,
        'price': item.price
        }
        for item in order_items
    ]

    return JsonResponse(data, safe=False)


@csrf_exempt
def add_to_order(request, product_id):
    try:
        product = Product.objects.get(id=product_id)

        order, created = Order.objects.get_or_create(
            status="pending", defaults={"total_price": 0}
        )

        order_item, created = OrderItem.objects.get_or_create(
            order=order, product=product, defaults={"quantity": 1}
        )

        if not created:
            order_item.quantity += 1
            order_item.save()

        return JsonResponse(
            {"success": True, "order_items": get_order_items_data(order)}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def update_order_item(request, item_id):
    try:
        data = json.loads(request.body)
        change = data.get("change", 0)

        order_item = OrderItem.objects.get(id=item_id)
        order_item.quantity += change

        if order_item.quantity <= 0:
            order_item.delete()
        else:
            order_item.save()

        return JsonResponse(
            {"success": True, "order_items": get_order_items_data(order_item.order)}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def complete_order(request):
    try:

        order = Order.objects.filter(status="pending").first()

        if not order or not order.items.exists():
            raise Exception("No active order to complete")

        order.status = "success"
        order.total_price = order.get_total_price()
        order.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_active_order(request):
    try:
        order = Order.objects.filter(status="pending").first()
        if order:
            return JsonResponse(
                {"success": True, "order_items": get_order_items_data(order)}
            )
        return JsonResponse({"success": True, "order_items": []})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_recent_orders(request):
    try:
        orders = Order.objects.filter(status="success").order_by("-created_at")[:8]
        orders_data = [
            {
                "id": order.id,
                "order_id": order.order_id,
                "total_price": float(order.total_price),
                "status": order.status,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "item_count": order.items.count(),
            }
            for order in orders
        ]

        return JsonResponse({"success": True, "orders": orders_data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def get_order_items_data(order):
    return [
        {
            "id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.name,
            "product_price": float(item.product.selling_price),
            "quantity": item.quantity,
        }
        for item in order.items.all()
    ]


def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    form = CancelOrderForm()

    if request.method == "POST":
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data["reason"]
            context = form.cleaned_data["context"]

            Report.objects.create(order=order, context=reason, dec=context)
            messages.success(request, "Order Canceled Successful")
            return redirect("home")
        messages = "an error occured canceling order"
        return messages
    context = {"form": form}
    return render(request, "main/home.html", context)


def products(request):
    products = Product.objects.select_related('category').all()
    categories = Category.objects.all()

    status_filter = request.GET.get('status', 'all')
    category_filter = request.GET.get('category', '')
    search_term = request.GET.get('search', '').lower()
    response_format = request.GET.get('format', 'html') 

    if status_filter != 'all':
        products = products.filter(status=status_filter)
    if category_filter:
        products = products.filter(category_id=category_filter)
    if search_term:
        products = products.filter(name__icontains=search_term)

    if response_format == 'json':
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'stock_quantity': product.stock_quantity,
                'status': product.status,
                'status_display': product.get_status_display(),
                'selling_price': str(product.selling_price),
                'image': product.image.url if product.image else ''
            })
        return JsonResponse({'products': products_data})

    context = {
        "products": products,
        "categories": categories
    }
    return render(request, "main/products.html", context)


def product_detail(request, product_id):
    try:
        product = Product.objects.select_related('category').get(id=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'category': product.category.name if product.category else '',
            'stock_quantity': product.stock_quantity,
            'status': product.status,
            'status_display': product.get_status_display(),
            'selling_price': str(product.selling_price),
            'description': product.description,
            'image': product.image.url if product.image else ''
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


def reports(request):
    reports = Report.objects.all()
    context = {"reports": reports}
    return render(request, "main/reports.html", context)


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully')
    return redirect('products')


def orders(request):
    return render(request, 'main/orders.html')

def filter_orders(request):

    time_filter = request.GET.get('time_filter', 'today')
    status_filter = request.GET.get('status_filter', 'all')
    custom_date = request.GET.get('custom_date', None)
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    if time_filter == 'today':
        start_date = today_start
        end_date = today_end
    elif time_filter == 'yesterday':
        start_date = today_start - timedelta(days=1)
        end_date = today_start
    elif time_filter == 'week':
        start_date = today_start - timedelta(days=today_start.weekday())
        end_date = today_end
    elif time_filter == 'month':
        start_date = today_start.replace(day=1)
        end_date = today_end
    elif time_filter == 'custom' and custom_date:
        try:
            custom_date = datetime.strptime(custom_date, '%Y-%m-%d')
            start_date = timezone.make_aware(custom_date)
            end_date = start_date + timedelta(days=1)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid time filter'}, status=400)
    
    orders_query = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lt=end_date
    )
    
    if status_filter != 'all':
        orders_query = orders_query.filter(status=status_filter)
    
    total_orders = orders_query.count()
    total_sales = orders_query.aggregate(total=Sum('total_price'))['total'] or 0.00
    pending_orders = orders_query.filter(status='pending').count()
    
    orders_data = []
    for order in orders_query.order_by('-created_at'):
        orders_data.append({
            'id': order.id,
            'order_id': order.order_id,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'item_count': order.get_order_quantity(),
            'total_price': float(order.total_price),
            'status': order.status,
            'status_display': order.get_status_display()
        })
    
    return JsonResponse({
        'total_orders': total_orders,
        'total_sales': total_sales,
        'pending_orders': pending_orders,
        'orders': orders_data
    })

def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        if order.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Only pending orders can be canceled'})
        
        order.status = 'canceled'
        order.is_canceled = True
        order.save()
        
        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)

def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order.delete()
        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)



def reports(request):
    return render(request, "main/reports.html", {
        "reports": Report.objects.select_related('order').all()
    })

def filter_reports(request):
   
    time_filter = request.GET.get('time_filter', 'all')
    type_filter = request.GET.get('type_filter', 'all')
    custom_date = request.GET.get('custom_date', None)
    
    reports_query = Report.objects.select_related('order').all()
    
    if time_filter != 'all':
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if time_filter == 'today':
            start_date = today_start
            end_date = today_start + timedelta(days=1)
        elif time_filter == 'yesterday':
            start_date = today_start - timedelta(days=1)
            end_date = today_start
        elif time_filter == 'week':
            start_date = today_start - timedelta(days=today_start.weekday())
            end_date = today_start + timedelta(days=7)
        elif time_filter == 'month':
            start_date = today_start.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif time_filter == 'custom' and custom_date:
            try:
                custom_date = datetime.strptime(custom_date, '%Y-%m-%d')
                start_date = timezone.make_aware(custom_date)
                end_date = start_date + timedelta(days=1)
            except ValueError:
                return JsonResponse({'error': 'Invalid date format'}, status=400)
        
        reports_query = reports_query.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
    
    if type_filter != 'all':
        if type_filter == 'order_cancel':
            reports_query = reports_query.filter(
                Q(context__icontains='cancel') | 
                Q(context__icontains='cancellation')
            )
        elif type_filter == 'system':
            reports_query = reports_query.filter(
                Q(context__icontains='system') | 
                Q(context__icontains='error') |
                Q(context__icontains='warning')
            )
        elif type_filter == 'other':
            reports_query = reports_query.exclude(
                Q(context__icontains='cancel') | 
                Q(context__icontains='cancellation') |
                Q(context__icontains='system') | 
                Q(context__icontains='error') |
                Q(context__icontains='warning')
            )
    
    reports_data = []
    for report in reports_query.order_by('-created_at'):
        reports_data.append({
            'id': report.id,
            'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
            'context': report.context,
            'dec': report.dec,
            'order_id': report.order.id if report.order else None,
            'order_number': report.order.order_id if report.order else None
        })
    
    return JsonResponse({
        'reports': reports_data
    })

def report_detail(request, report_id):
    try:
        report = Report.objects.select_related('order').get(id=report_id)
        data = {
            'id': report.id,
            'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
            'context': report.context,
            'dec': report.dec,
            'order_id': report.order.id if report.order else None,
            'order_number': report.order.order_id if report.order else None
        }
        return JsonResponse(data)
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)

def delete_report(request, report_id):
    try:
        report = Report.objects.get(id=report_id)
        report.delete()
        return JsonResponse({'success': True})
    except Report.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'}, status=404)