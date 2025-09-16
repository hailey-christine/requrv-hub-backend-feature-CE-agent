from pydantic import BaseModel, EmailStr, Field


class SignUpDto(BaseModel):
    email: EmailStr
    password: str
    mandatoryPrivacy: bool = Field(False)
    terms: bool = Field(False)


class ConfirmAccountDto(BaseModel):
    otp: str
    email: EmailStr

class ResendOTPDto(BaseModel):
    email: EmailStr


class SignInDto(BaseModel):
    email: EmailStr
    password: str


class CompanyInfo(BaseModel):
    # USER FIELDS
    name: str = Field(..., description="Devi inserire il nome")
    surname: str = Field(..., description="Devi inserire il cognome")

    # COMPANY FIELDS
    companyName: str = Field(..., description="Devi inserire il nome dell'azienda")
    companyAddress: str = Field(
        ..., description="Devi inserire l'indirizzo dell'azienda"
    )
    companyEmail: str = Field(
        ..., description="Devi inserire l'indirizzo email aziendale"
    )
    companyCity: str = Field(..., description="Devi inserire la città dell'azienda")
    companyZip: str = Field(..., description="Devi inserire il CAP dell'azienda")
    companyVat: str = Field(
        ..., description="Devi inserire la partita IVA dell'azienda"
    )
    companyFiscalCode: str | None = Field(None, description="Partita IVA facoltativa")
    companySdi: str = Field(..., description="Devi inserire il codice SDI dell'azienda")

    # COMPANY DETAILS
    companyVision: str | None = Field(None, description="Visione aziendale facoltativa")
    companyMission: str | None = Field(
        None, description="Missione aziendale facoltativa"
    )
    companyProducts: str | None = Field(
        None, description="Prodotti aziendali facoltativi"
    )
    companyToneOfVoice: str | None = Field(
        None, description="Tono di voce aziendale facoltativo"
    )
    companyIncome: str | None = Field(None, description="Ricavo aziendale facoltativo")
    companyGoals: str | None = Field(
        None, description="Obiettivi aziendali facoltativi"
    )
    companyLongTermGoals: str | None = Field(
        None, description="Obiettivi a lungo termine aziendali facoltativi"
    )
    attachments: list[str] | None = Field(None, description="Allegati facoltativi")


################### OUTPUT #######################


class SignInOutput(BaseModel):
    jwt: str
    is_first_login: bool


class MeOutput(BaseModel):
    id: str
    name: str | None
    surname: str | None
    email: EmailStr
    is_first_login: bool


class MyCompanyOutput(BaseModel):
    id: str
    name: str
    email: EmailStr
    vatNumber: str
    address: str
    city: str
    zipCode: str
    country: str | None = Field(default=None)
    sdi: str | None = Field(default=None)
    pec: str | None = Field(default=None)
