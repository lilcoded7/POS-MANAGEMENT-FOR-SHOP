from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from shop.models.products import Product, Category
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from shop.models.orders import Order
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shop.models.order_items import OrderItem
from shop.models.cancel_order import CancelOrder
from shop.forms import *
from shop.models.reports import Report
from django.db.models import Sum
from django.contrib import messages
from datetime import datetime, time, timedelta
from django.utils import timezone
from shop.models.workers import Worker
from django.contrib.auth import get_user_model, logout
from django.db.models import Q
from shop.serializer import ActivateAccountSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models.activate_accounts import ActivateAccount
from shop.models.customers import Customer

User = get_user_model()

import json

def has_activated_account(request):
    if request.user.has_activated == False:
        messages.error(request, "Contact Support to activate your Account")
        logout(request)
        return redirect("login_view")

@login_required
def home(request):
    today = timezone.localdate()
    cancel_form = CancelOrderForm()

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
                "status": product.status,
                "category": product.category.name if product.category else "",
            }
            for product in products
        ]
        return JsonResponse({"products": products_data})

    order_items = [
        {
            "order": order,
            "order_items": OrderItem.objects.filter(order=order),
        }
        for order in Order.objects.all()
    ]

    if request.method == "POST":
        product_name = request.POST["name"]
        products = Product.objects.filter(name__icontains=product_name)

    context = {
        "products": products,
        "cancel_form": cancel_form,
        "categories": categories,
        "order_items": order_items,
        "today_orders": today_orders,
        "orders": orders,
        "reasons": reasons,
        "form": form,
        "total_sales": round(float(total_sales or 0), 2),
        "order_count": order_count or 0,
        "average_order_value": round(float(average_order_value or 0), 2),
        "canceled_order": canceled_order or 0,
    }
    return render(request, "main/home.html", context)

def get_order_details(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = OrderItem.objects.filter(order=order).select_related("product")

        order_data = {
            "order_id": order.order_id,
            "created_at": order.created_at,
            "status": order.get_status_display(),
            "total_price": str(order.total_price),
            "is_canceled": order.is_canceled,
        }

        items_data = []
        for item in order_items:
            if item.product:
                items_data.append(
                    {
                        "product": {
                            "name": item.product.name,
                            "selling_price": str(item.product.selling_price),
                        },
                        "quantity": item.quantity,
                        "get_total_product_price": str(item.get_total_product_price()),
                    }
                )
            else:
                items_data.append(
                    {
                        "product": {
                            "name": "Product no longer available",
                            "selling_price": "0.00",
                        },
                        "quantity": item.quantity,
                        "get_total_product_price": "0.00",
                    }
                )

        return JsonResponse(
            {"success": True, "order": order_data, "order_items": items_data}
        )

    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"}, status=404)

@csrf_exempt
def add_to_order(request, product_id):
    try:
        product = Product.objects.get(id=product_id)

        order, created = Order.objects.get_or_create(
            status="pending", defaults={"total_price": 0}
        )

        order_item, created = OrderItem.objects.get_or_create(
            order=order, product=product, defaults={"quantity": 0}
        )

        if not created:
            order_item.quantity += 1
            order_item.save()
        else:
            order_item.quantity = 1
            order_item.save()

        return JsonResponse(
            {"success": True, "order_items": get_order_items_data(order)}
        )
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "error": "Product not found"}, status=404)
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
    except OrderItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order item not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@csrf_exempt
def complete_order(request):
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number', '')
        
        if not phone_number or len(phone_number) < 10:
            return JsonResponse({"success": False, "error": "Valid phone number is required"}, status=400)

        customer, created = Customer.objects.get_or_create(phone_number=phone_number)

        order = Order.objects.filter(status="pending").first()
         
        if not order or not order.items.exists():
            return JsonResponse({"success": False, "error": "No active order to complete"}, status=400)

        order.status = "success"
        order.total_price = order.get_total_price()
        order.customer = customer
        order.save()
        
        Report.objects.create(
            user=request.user,
            order=order,
            context=f"order with the ID: {order.order_id} Completed Successfully",
            dec=f"order with the ID: {order.order_id} Completed Successfully",
        )

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
            "product_id": item.product.id if item.product else None,
            "product_name": item.product.name if item.product else "Product not available",
            "product_price": float(item.product.selling_price) if item.product else 0.0,
            "quantity": item.quantity,
        }
        for item in order.items.all()
    ]

@login_required
def products(request):
    
    product_form = ProductForm()
    category_form = CategoryForm()
    products = Product.objects.select_related("category").all()
    categories = Category.objects.all()

    status_filter = request.GET.get("status", "all")
    category_filter = request.GET.get("category", "")
    search_term = request.GET.get("search", "").lower()
    response_format = request.GET.get("format", "html")

    if status_filter != "all":
        products = products.filter(status=status_filter)
    if category_filter:
        products = products.filter(category_id=category_filter)
    if search_term:
        products = products.filter(name__icontains=search_term)

    if response_format == "json":
        products_data = []
        for product in products:
            products_data.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category.name if product.category else "",
                    "status": product.status,
                    "status_display": product.get_status_display(),
                    "selling_price": str(product.selling_price),
                    "image": product.image.url if product.image else "",
                }
            )
        return JsonResponse({"products": products_data})

    context = {
        "products": products,
        "categories": categories,
        "product_form": product_form,
        "category_form": category_form,
    }
    return render(request, "main/products.html", context)


def product_detail(request, product_id):
    try:
        product = Product.objects.select_related("category").get(id=product_id)
        data = {
            "id": product.id,
            "name": product.name,
            "category": product.category.name if product.category else "",
            "status": product.status,
            "status_display": product.get_status_display(),
            "selling_price": str(product.selling_price),
            "description": product.description,
            "image": product.image.url if product.image else "",
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

@login_required
def reports(request):
   
    reports = Report.objects.all()
    context = {"reports": reports}
    return render(request, "main/reports.html", context)

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Report.objects.create(
        user=request.user,
        context=f"Product: {product.name} Deleted Successfully",
        dec=f"Product: {product.name} Deleted Successfully",
    )
    product.delete()
    messages.success(request, "Product deleted successfully")
    return redirect("products")

@login_required
def orders(request):
    
    return render(request, "main/orders.html")

def filter_orders(request):
    time_filter = request.GET.get("time_filter", "today")
    status_filter = request.GET.get("status_filter", "all")
    custom_date = request.GET.get("custom_date", None)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    if time_filter == "today":
        start_date = today_start
        end_date = today_end
    elif time_filter == "yesterday":
        start_date = today_start - timedelta(days=1)
        end_date = today_start
    elif time_filter == "week":
        start_date = today_start - timedelta(days=today_start.weekday())
        end_date = today_end
    elif time_filter == "month":
        start_date = today_start.replace(day=1)
        end_date = today_end
    elif time_filter == "custom" and custom_date:
        try:
            custom_date = datetime.strptime(custom_date, "%Y-%m-%d")
            start_date = timezone.make_aware(custom_date)
            end_date = start_date + timedelta(days=1)
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)
    else:
        return JsonResponse({"error": "Invalid time filter"}, status=400)

    orders_query = Order.objects.filter(
        created_at__gte=start_date, created_at__lt=end_date
    )

    if status_filter != "all":
        orders_query = orders_query.filter(status=status_filter)

    total_orders = orders_query.count()
    total_sales = orders_query.aggregate(total=Sum("total_price"))["total"] or 0.00
    pending_orders = orders_query.filter(status="pending").count()

    orders_data = []
    for order in orders_query.order_by("-created_at"):
        orders_data.append(
            {
                "id": order.id,
                "order_id": order.order_id,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "item_count": order.get_order_quantity(),
                "total_price": float(order.total_price),
                "status": order.status,
                "status_display": order.get_status_display(),
            }
        )

    return JsonResponse(
        {
            "total_orders": total_orders,
            "total_sales": total_sales,
            "pending_orders": pending_orders,
            "orders": orders_data,
        }
    )

@login_required
def cancel_order(request, order_id):
   
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        reason_id = request.POST.get("reason")
        notes = request.POST.get("notes", "")

        try:
            reason = CancelOrder.objects.get(id=reason_id)

            order.status = "canceled"
            order.is_canceled = True
            order.save()

            Report.objects.create(
                user=request.user,
                order=order,
                context=f"Order with the ID: {order.order_id} Canceled Reason: {reason}",
                dec=notes,
            )

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": True, "message": "Order canceled successfully"}
                )
            else:
                messages.success(request, "Order canceled successfully")
                return redirect("home")

        except CancelOrder.DoesNotExist:
            error_msg = "Invalid cancellation reason"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": error_msg}, status=400
                )
            else:
                messages.error(request, error_msg)
                return redirect("home")

    cancel_form = CancelOrderForm()
    return render(
        request,
        "main/home.html",
        {"cancel_form": cancel_form, "orders": Order.objects.all()},
    )

def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order.delete()
        return JsonResponse({"success": True})
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"}, status=404)

@login_required
def reports_view(request):
    
    return render(
        request,
        "main/reports.html",
        {"reports": Report.objects.select_related("order").all()},
    )

def filter_reports(request):
    time_filter = request.GET.get("time_filter", "all")
    type_filter = request.GET.get("type_filter", "all")
    custom_date = request.GET.get("custom_date", None)

    reports_query = Report.objects.select_related("order").all()

    if time_filter != "all":
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if time_filter == "today":
            start_date = today_start
            end_date = today_start + timedelta(days=1)
        elif time_filter == "yesterday":
            start_date = today_start - timedelta(days=1)
            end_date = today_start
        elif time_filter == "week":
            start_date = today_start - timedelta(days=today_start.weekday())
            end_date = today_start + timedelta(days=7)
        elif time_filter == "month":
            start_date = today_start.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif time_filter == "custom" and custom_date:
            try:
                custom_date = datetime.strptime(custom_date, "%Y-%m-%d")
                start_date = timezone.make_aware(custom_date)
                end_date = start_date + timedelta(days=1)
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

        reports_query = reports_query.filter(
            created_at__gte=start_date, created_at__lt=end_date
        )

    if type_filter != "all":
        if type_filter == "order_cancel":
            reports_query = reports_query.filter(
                Q(context__icontains="cancel") | Q(context__icontains="cancellation")
            )
        elif type_filter == "system":
            reports_query = reports_query.filter(
                Q(context__icontains="system")
                | Q(context__icontains="error")
                | Q(context__icontains="warning")
            )
        elif type_filter == "other":
            reports_query = reports_query.exclude(
                Q(context__icontains="cancel")
                | Q(context__icontains="cancellation")
                | Q(context__icontains="system")
                | Q(context__icontains="error")
                | Q(context__icontains="warning")
            )

    reports_data = []
    for report in reports_query.order_by("-created_at"):
        reports_data.append(
            {
                "id": report.id,
                "created_at": report.created_at.strftime("%Y-%m-%d %H:%M"),
                "context": report.context,
                "dec": report.dec,
                "order_id": report.order.id if report.order else None,
                "order_number": report.order.order_id if report.order else None,
            }
        )

    return JsonResponse({"reports": reports_data})

def report_detail(request, report_id):
    try:
        report = Report.objects.select_related("order").get(id=report_id)
        data = {
            "id": report.id,
            "created_at": report.created_at.strftime("%Y-%m-%d %H:%M"),
            "context": report.context,
            "dec": report.dec,
            "order_id": report.order.id if report.order else None,
            "order_number": report.order.order_id if report.order else None,
        }
        return JsonResponse(data)
    except Report.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)

def delete_report(request, report_id):
    try:
        report = Report.objects.get(id=report_id)
        report.delete()
        return JsonResponse({"success": True})
    except Report.DoesNotExist:
        return JsonResponse({"success": False, "error": "Report not found"}, status=404)

@login_required
def product_inventory(request):
    
    products = Product.objects.all().order_by("-created_at")
    categories = Category.objects.all()

    if request.method == "POST":
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            product_id = request.POST.get("product_id")
            if product_id:
                product = get_object_or_404(Product, id=product_id)
                product_form = ProductForm(
                    request.POST, request.FILES, instance=product
                )
                product_form.save()
                Report.objects.create(
                    user=request.user,
                    context=f"Product: {product.name} Updated Successfully",
                    dec=f"Product: {product.name} Updated Successfully",
                )
                messages.success(request, "Product updated successfully!")
            else:
                product_form.save()
                Report.objects.create(
                    user=request.user,
                    context=f"Product: {product_form.instance.name} Created Successfully",
                    dec=f"Product: {product_form.instance.name} Created Successfully",
                )
                messages.success(request, "Product created successfully!")
            return redirect("product_inventory")
    else:
        product_form = ProductForm()

    category_form = CategoryForm(request.POST or None)
    if request.method == "POST" and "category_submit" in request.POST:
        if category_form.is_valid():
            category_form.save()
            messages.success(request, "Category created successfully!")
            return redirect("product_inventory")

    context = {
        "products": products,
        "categories": categories,
        "product_form": product_form,
        "category_form": category_form,
    }
    return render(request, "main/products.html", context)

def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    data = {
        "name": product.name,
        "description": product.description,
        "category": product.category.name if product.category else None,
        "status": product.status,
        "status_display": product.get_status_display(),
        "selling_price": str(product.selling_price),
        "image": product.image.url if product.image else None,
    }
    return JsonResponse(data)

def delete_product_api(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        Report.objects.create(
            user=request.user,
            context=f"Product: {product.name} Deleted Successfully",
            dec=f"Product: {product.name} Deleted Successfully",
        )
        product.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@login_required
def workers(request):
    
    workers = Worker.objects.all()
    form = CreateWorkerForm()
    return render(request, "main/workers.html", {"workers": workers, "form": form})

def delete_worker(request, worker_id):
    worker = get_object_or_404(Worker, id=worker_id)
    Report.objects.create(
        user=request.user,
        context=f"Worker: {worker.name} Deleted Successfully",
        dec=f"Worker: {worker.name} Deleted Successfully",
    )
    worker.user.delete()
    worker.delete()
    messages.success(request, "Worker deleted successfully ")
    return redirect("workers")

def create_worker(request):
    
    if request.method == "POST":
        form = CreateWorkerForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            username = name.replace(" ", "").lower()

            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists.")
                return redirect("workers")
            
            if User.objects.filter(email=email).exists():
                messages.error(request, f"Email '{email}' is already in use.")
                return redirect("workers")

            user = User.objects.create(username=username, email=email, password="0000")

            worker = form.save(commit=False)
            worker.user = user
            worker.save()

            Report.objects.create(
                user=request.user,
                context=f"Worker: {worker.name} Created Successfully",
                dec=f"Worker: {worker.name} Created Successfully",
            )

            messages.success(
                request,
                f"Worker '{name}' created successfully with username '{username}', email '{email}', and default password '0000'.",
            )
            return redirect("workers")

        else:
            workers = Worker.objects.all()
            return render(
                request, "main/workers.html", {"workers": workers, "form": form}
            )

    return redirect("workers")

class GetActivationCode(APIView):
    def get(self, request):
        activation_code = ActivateAccount.objects.all()
        code = ActivateAccountSerializer(activation_code, many=True).data
        return Response({"data": code})
    


def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()  # requires related_name="items" on OrderItem
    print(order_items)  # debug, better use logging instead of print()

    context = {
        "order": order,
        "order_items": order_items,
    }
    return render(request, "main/invoice.html", context)