
from service_manager.exceptions import InvalidDataError

PAYMENT_METHODS = {
    "cash": "Cash on delivery",
    "card_on_delivery": "Card on delivery",
    "online": "Online payment",
}

PAYMENT_STATUSES = {
    "pending",
    "paid",
    "cancelled",
}

DELIVERY = {
    "pickup": "Pickup at the clinic",
    "clinic_courier": "Clinic courier delivery",
    "nova_poshta": "Nova Poshta delivery",
}

def select_payment_method():
    print("""Choose a payment method:
          1. Cash on delivery
          2. Card on delivery
          3. Online payment""")
    while True:
        try:
            choose = int(input("input a payment method"))
            if choose == 1:
                return "cash"
            elif choose == 2:
                return "card_on_delivery"
            elif choose == 3:
                return "online"
            else: 
                print("Invalid choice. Please enter a number from 1 to 3.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def select_fulfillment_method(): 
    print("""Choose delivery:
          1. Pickup at the clinic
          2. Clinic courier delivery
          3. Nova Poshta delivery""")
    while True:
        try:
            choose = int(input("enter  delivery method"))
            if choose == 1:
                return "pickup"
            elif choose == 2:
                return "clinic_courier"
            elif choose == 3:
                return "nova_poshta"
            else: 
                    print("Invalid choice. Please enter a number from 1 to 3.")
        except ValueError:
                print("Invalid input. Please enter a number.")   

def enter_delivery_address(fulfillment_method):
    if fulfillment_method not in DELIVERY:
        raise InvalidDataError("Invalid fulfillment method.")
    if fulfillment_method == "pickup":
        return None
    if fulfillment_method == "clinic_courier":
        while True:
            choose = input("Enter the delivery address: ").strip()
            if choose == "":
                print("Invalid input. Please enter address.")
            else:
                return choose
    if fulfillment_method == "nova_poshta":
        while True:
            choose1 = input("Enter the city and the Nova Poshta branch or parcel locker number: ").strip()
            if choose1 == "":
                print("Invalid input. Please enter address.")
            else:
                return choose1         

if __name__ == "__main__":
    payment = select_payment_method()
    print("Selected payment method:", PAYMENT_METHODS[payment])

    fulfillment = select_fulfillment_method()
    print("Selected fulfillment method:", DELIVERY[fulfillment])   

    delivery_address = enter_delivery_address(fulfillment)
    print("address delivery:", delivery_address )