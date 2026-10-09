from dataclasses import dataclass
from typing import List


# --- Data Models ---
@dataclass
class Product:
    id: int
    name: str
    price: float


@dataclass
class Customer:
    id: int
    name: str


@dataclass
class Order:
    id: int
    customer_id: int
    product_ids: List[int]


@dataclass
class OrderReport:
    customer_name: str
    product_names: List[str]
    total_order_value: float


class ProductDataSource:
    def get_all(self) -> List[Product]:
        return fetch_products_from_db()


class CustomerDataSource:
    def get_all(self) -> List[Customer]:
        return fetch_customers_from_db()


class OrderDataSource:
    def get_all(self) -> List[Order]:
        return fetch_orders_from_db()



      
"""
Task Description:
-----------------
You are given data models for Product, Customer, Order, and OrderReport, along with
data source interfaces intended to supply lists of these entities. The goal is to
implement an OrderReportService that generates order reports. Each report should
include:

1. The customer's name.
2. A list of product names included in the order.
3. The total value of the order (sum of product prices).
"""
      
      
class OrderReportService:
    
    def get_ordered_products(self, order: Order):
        products = ProductDataSource().get_all()
        product_prices = 0
        product_names = []
        for product in products:
            if product.id in order.product_ids:
                product_prices += product.price
                product_names.append(product.name)
        return {"product_names": product_names, "product_totle": product_prices}

    def get_customer_name(self, order: Order):
        customers = CustomerDataSource().get_all()
        for customer in customers:
            if customer.id == order.customer_id:
                return customer.name
        return ""

    def generate_order_reports(self) -> List[OrderReport]:
        orders = OrderDataSource().get_all()
            
        results = []
        
        for order in orders:
            product_details = self.get_ordered_products(order)
            results.append(OrderReport(customer_name=self.get_customer_name(order), product_names=product_details["product_names"], total_order_value=product_details["product_totle"]))
         
        return results
        
