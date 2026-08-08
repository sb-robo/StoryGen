# Sample Payments Platform BRD

## 1. Overview

Build a small B2B payments portal where merchants can accept card payments,
view settlements, and manage team access.

## 2. Authentication

Merchants must sign in with email and password. Failed login attempts should
show a clear error. Sessions expire after inactivity.

## 3. Payment collection

Merchants can create a payment request for a customer amount and currency.
Successful payments generate a receipt reference. Declined payments show the
decline reason.

## 4. Settlements

Merchants can view a list of settlements with date, amount, and status.
Settlement detail shows the underlying payment references.

## 5. Team access

Account owners can invite teammates by email and assign Admin or Viewer roles.
Viewers cannot create payment requests.
