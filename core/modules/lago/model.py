from pydantic import BaseModel, Field
from typing import Optional


class CustomerBillingConfiguration(BaseModel):
    invoice_grace_period: int | None = Field(5)
    payment_provider: str | None = Field("stripe")
    provider_customer_id: str | None
    sync: bool | None = Field(True)
    sync_with_provider: bool | None = Field(True)
    document_locale: str | None = Field("it")


class CompanyInfo(BaseModel):
    external_id: str
    name: str
    legal_name: str | None
    address_line1: str
    address_line2: Optional[str]
    email: str | None
    city: str
    zipcode: str
    country: str | None = Field("IT")
    currency: str | None = Field("EUR")
    tax_identification_number: str
    legal_number: str | None
    logo_url: str | None
    phone: str | None
    state: str | None
    timezone: str | None = Field("Europe/Rome")
    url: str | None
    billing_configuration: CustomerBillingConfiguration
