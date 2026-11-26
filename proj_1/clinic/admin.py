from django.contrib import admin
from .models import (
    User,
    Client,
    Employee,
    Product,
    Procedure,
    Order,
    OrderProduct,
    OrderProcedure,
    EmployeeRating,
)

admin.site.register(User)
admin.site.register(Client)
admin.site.register(Employee)
admin.site.register(Product)
admin.site.register(Procedure)
admin.site.register(Order)
admin.site.register(OrderProduct)
admin.site.register(OrderProcedure)
admin.site.register(EmployeeRating)


