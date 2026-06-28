# Sample Inputs

Paste any of these into the app to see it in action.

## 1. User Account Security (the classic demo)
```
User Account Security
- Users can reset their password through email verification.
- Passwords must contain at least 8 characters.
- Accounts lock after 5 consecutive failed login attempts.
```

## 2. Telecom-flavoured: Session Timer (domain differentiator)
```
Bearer Session Inactivity Timer
- A data bearer is released after 30 minutes of inactivity.
- Any uplink or downlink packet resets the inactivity timer.
- The timer must not fire while a voice call is active on the bearer.
- On timer expiry, a Delete Session Request is sent to the gateway.
```

## 3. API Rate Limiter
```
API Rate Limiter
- Each API key may make 100 requests per minute.
- Requests beyond the limit return HTTP 429.
- The counter resets at the start of each minute window.
- Admin keys are exempt from rate limiting.
```

## 4. Shopping Cart Checkout
```
Checkout
- A cart must contain at least 1 item before checkout is allowed.
- Orders over $50 qualify for free shipping.
- A discount code reduces the total by 10%, but only one code per order.
- Payment must be authorized before the order is confirmed.
```
