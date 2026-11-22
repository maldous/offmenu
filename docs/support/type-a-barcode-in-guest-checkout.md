# Type a barcode when the camera is blocked

In the main OffMenu app, open **Scan groceries**, then **Open my checkout**.
If the camera is blocked, leave it off and open **Type or use a USB / Bluetooth
scanner**. Select the **Barcode** field and type the printed digits, including
any leading zeros. If you already have a compatible scanner that types into
the field, you can use it there. Choose **Find**.

If you see **Enter a barcode with 4–32 digits**, return to **Barcode**, correct
the value and choose **Find** again. A value rejected by this check is not added
to the checkout. An unknown item shown on the draft receipt is not a verified
product match. Check the package and review the draft before confirming any
pantry change; use **Void last item** if the unwanted item is the latest one.

To try the camera instead, allow it in your browser’s site settings and retry.
You do not need to allow it to type a barcode.

## Review notes (not help copy)

- Applies to **Scan groceries** in the main app Guest checkout at exact
  source `de5fdc7d`, not the separate retained scanner’s **Type code**
  dialog. The [scanner guide](../scanner-user-guide.md) describes that
  different screen.
- The main app accepts 4–32 digits and preserves leading zeros. The
  current source does not automatically refocus invalid input; use the
  **Barcode** field to retry.
- Separate local QA candidate `273c0cbc` demonstrated automatic focus
  return after an invalid submission. Do not describe that behavior as
  installed until the released source includes it. This page does not
  certify hardware pairing, a physical camera, or complete catalogue coverage.
