from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
    ("admin", "Admin"),
    ("client", "Client"),
    ("employee", "Employee"),
]
    id = models.UUIDField(primary_key=True)
    username = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


    class Meta:
        db_table = "users"
        managed = False

    def __str__(self):
        return self.username    

class Client(models.Model):
    user = models.OneToOneField( User,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="user_id",
        related_name="client")
    email = models.CharField(max_length=255, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True) 


    class Meta:
        db_table = "clients"
        managed = False 

    def __str__(self):
        return self.user.username 


class Employee(models.Model):
    user = models.OneToOneField( User,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="user_id",
        related_name="employee")
    specialization = models.CharField(max_length=100, null=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2, default=20000)
    procedure_percent = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    sales_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10)


    class Meta:
        db_table = "employees"
        managed = False 
    
    def __str__(self):
        return self.user.username 



class Product(models.Model):
    id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()  
    reserved_quantity = models.PositiveIntegerField(default=0)
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "products"
        managed = False 
        
    def __str__(self):
        return self.product_name  

class Procedure(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    service_code = models.CharField(max_length=200, unique = True) 
    category = models.CharField(max_length=200) 
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()         
    is_active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "procedures"
        managed = False 
            
    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ("Scheduled", "scheduled"),
        ("In Progress", "in progress"),
        ("Completed", "completed"),
        ("Cancelled", "cancelled"),
    ]
    PAYMENT_METHOD = [
        ("cash", "Cash"),
        ("card_on_delivery", "Card_on_delivery"),
        ("online", "Online"),
    ]

    PAYMENT_STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    FULFILLMENT_METHOD = [
        ("pickup", "Pickup"),
        ("clinic_courier", "Clinic_courier"),
        ("nova_poshta", "Nova_poshta"),
    ]
    id = models.UUIDField(primary_key=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        db_column="client_id",
        related_name="orders"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    appointment_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD, null=True, blank=True)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default="pending")
    fulfillment_method = models.CharField(max_length=50, choices=FULFILLMENT_METHOD, null=True, blank=True)
    delivery_address = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        managed = False 
                
    def __str__(self):
        return str(self.id)

class OrderProduct(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="order_products"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column="order_id",
        related_name="products"
    )
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_quantity = models.PositiveIntegerField() 

    class Meta:
        db_table = "order_products"
        managed = False 
                
    def __str__(self):
        return f"{self.product_name} — {self.product_quantity}"

class OrderProcedure(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column="order_id",
        related_name="procedures"
    )
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        db_column="procedure_id",
        related_name="order_procedures"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        db_column="employee_id",
        related_name="order_procedures"
    )
    quantity = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
            db_table = "order_procedures"
            managed = False 
                    
    def __str__(self):
        return self.procedure.name

class EmployeeProcedure(models.Model):
    pk = models.CompositePrimaryKey("employee", "procedure")
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        db_column="procedure_id",
        related_name="employee_procedures"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        db_column="employee_id",
        related_name="employee_procedures"
    )
    class Meta:
        db_table = "employee_procedures"
        managed = False 
                        
    def __str__(self):
        return f"{self.employee.user.username}: {self.procedure.name}"


class EmployeeRating(models.Model):
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        db_column="employee_id",
        related_name="employee_ratings"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        db_column="client_id",
        related_name="employee_ratings"
    )
    score = models.PositiveIntegerField()
    class Meta:
        db_table = "employee_rating"
        managed = False 
                            
    def __str__(self):
        return f"{self.employee.user.username}: {self.score}"


