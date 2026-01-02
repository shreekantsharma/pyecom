# Column Mapping & Assumptions

| Logical Field | Target Column Name | Assumed Source Column Variations (Case-Insensitive) | Handling Strategy |
| :--- | :--- | :--- | :--- |
| **Order ID** | `order_id` | `order id`, `id`, `order_no`, `order number` | Required. Rows with empty/null Order ID are dropped for calculations. |
| **Order Date** | `order_date` | `created at`, `order date`, `date`, `timestamp` | Required. Converted to datetime. Errors result in NaT. |
| **Order Status** | `order_status` | `status`, `order status`, `fulfillment status` | Required. Mapped to buckets (DELIVERED, RTO, UNDELIVERED, IN_TRANSIT) based on string matching. |
| **Payment Method** | `payment_method` | `payment method`, `payment mode`, `type` | Optional. Defaults to "Unknown" if missing. |
| **Product Name** | `product_name` | `product name`, `item name`, `title` | Required. Used for grouping. |
| **SKU** | `sku` | `sku`, `variant sku`, `item sku` | Optional. Used as fallback for product grouping if name is missing. |
| **State** | `state` | `shipping province`, `shipping state`, `state`, `province` | Required for Map. Normalized (e.g., "Delhi" -> "NCT of Delhi" normalization attempted). |
| **GMV Amount** | `gmv_amount` | `total`, `order total`, `gmv`, `amount`, `price` | Required. Non-numeric chars removed. Defaults to 0. |
| **Margin Amount** | `margin_amount` | `margin`, `profit`, `margin amount` | Optional. Used to calculate margin %. |
| **Margin %** | `margin_percent` | `margin %`, `margin percent`, `profit %` | Optional. Priority 1. |
| **Confirmation** | `confirmation_status`| `confirmation status`, `is confirmed` | Optional. Defaults to "Confirmed" if missing to avoid data loss. |
| **Return Status** | `return_status` | `return status`, `return_state` | Optional. Used for "Returned %" in product table. |
| **Sync Status** | `sync_status` | `synced`, `is_synced`, `failed_to_sync` | Optional. Used for "Synced Orders" logic. |

## Assumptions
1. **Synced Orders**: If no `sync_status` column is found, we assume ALL rows with a valid `order_id` are "Synced".
2. **In Transit Logic**: defined as `Shipped` + `Out for Delivery` + `In Transit` + `Undelivered` (as per user instruction "Undelivered" is included in In Transit count for logical grouping in the prompt, though typically it might be separate; following specific prompt instruction).
3. **Undelivered logic**: Explicitly "Undelivered" status string. Note: The prompt instruction says "IN_TRANSIT: ... + Undelivered". It also defines "UNDELIVERED: Undelivered". This implies "Undelivered" items count towards *both* the "In Transit" bucket (for the KPI numerator maybe?) and their own bucket?
    *Refined rule based on Prompt*:
    - Prompt says: `IN_TRANSIT: "Shipped" + "Out for Delivery" + "In Transit" (if exists) + "Undelivered" (Match the reference logic where IN_TRANSIT count includes Undelivered)`
    - Prompt also says: `UNDELIVERED: "Undelivered" (delivery attempt failed)`
    - *Interpretation*: When calculating the **KPI "In Transit %"**, the numerator includes 'Undelivered'. When showing the **sub-label**, we show distinct counts. When showing the **Donut**, 'Undelivered' might be its own slice or part of In Transit. I will treat 'Undelivered' as a status that *contributes* to the In Transit KPI numerator but stands alone as a status string.
4. **Dates**: If `order_date` is missing/invalid, those rows are excluded from daily charts but included in totals if possible (or dropped if date is critical for all views).
5. **Margin**: If both `margin_amount` and `margin_percent` are missing, Margin widgets will display 0 or "N/A".
6. **Currency**: Assumed INR (₹) for formatting.
