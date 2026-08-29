# Order, Payment, and Shipment are distinct Facts

An Order is the purchase (including delivery method as an attribute and fulfillment as its status). A Payment is a capture — one per Order except labeled duplicate charge. A Shipment is the carrier movement (0..1). Delivery and Fulfillment are not entities. Collapsing Payment into Order cannot represent double charge; inventing a Fulfillment aggregate duplicates Order status.

Status: accepted
