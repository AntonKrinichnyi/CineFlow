from fastapi import FastAPI

from routes import accounts, carts, movies, orders, payments

app = FastAPI()

app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(carts.router, prefix="/carts", tags=["carts"])
app.include_router(movies.router, prefix="/movies", tags=["movies"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
