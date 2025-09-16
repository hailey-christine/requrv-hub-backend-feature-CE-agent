import pyotp

from core.settings import settings

otp_key = settings.model_dump().get("requrv_otp_key") or ""

otp = pyotp.TOTP(otp_key, digits=6)
