from typing import Literal
from py_clob_client.clob_types import OrderArgs
from helpers.clob_client import create_clob_client

def create_and_submit_order(token_id: str, side: Literal['BUY'] | Literal['SELL'], price: float, size: int):
    client = create_clob_client()

    # Log the order details before submission
    print(f"\nSubmitting order:")
    print(f"Side: {side}")
    print(f"Price: {price}")
    print(f"Size: {size}")
    print(f"Token ID: {token_id}")

    # Create and sign the order
    order_args = OrderArgs(
        price=price,
        size=size,
        side=side,
        token_id=token_id,
    )
    
    try:
        signed_order = client.create_order(order_args)
        print("\nOrder signed successfully")
        
        # Submit the order
        resp = client.post_order(signed_order)
        print("\nOrder submission response:")
        print(resp)
        
        # Check if the order appears in open orders
        try:
            open_orders = client.get_open_orders()
            print("\nCurrent open orders:")
            print(open_orders)
        except Exception as e:
            print(f"\nError checking open orders: {str(e)}")
            
        print('Done!')
        return resp
        
    except Exception as e:
        print(f"\nError creating/submitting order: {str(e)}")
        raise