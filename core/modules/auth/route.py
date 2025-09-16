from typing import Annotated
from authx import TokenPayload
import bcrypt
import re
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import EmailStr
from core.services.lago.lago import create_customer
from core.services.litellm import create_key, create_team
from core.settings import auth
from core.modules.auth.model import (
    ConfirmAccountDto,
    MeOutput,
    MyCompanyOutput,
    ResendOTPDto,
    SignInDto,
    SignInOutput,
    SignUpDto,
    CompanyInfo,
)
from core.services.email import EmailParams, send_email
from core.services.otp import otp
from core.services.prisma import prisma
from prisma.models import User
from lago_python_client.models import Customer, CustomerBillingConfiguration

auth_router = APIRouter(prefix="/auth", tags=["auth"])
auth_scheme = HTTPBearer()


@auth_router.post("/sign-up")
async def sign_up(data: Annotated[SignUpDto, Body(embed=True, strict=True)]):
    _validate_input(data)  # Validate input data

    if await _check_user_exist(data.email):
        raise HTTPException(status_code=500, detail="User already exists")

    confirmation_otp = otp.now()
    user = None

    try:
        async with prisma.tx() as transaction:
            user = await transaction.user.create(
                data={
                    "password": _get_hashed_password(data.password),
                    "email": data.email.lower(),
                    "confirmation_token": confirmation_otp,
                }
            )
            # Simulate an error to test transaction rollback
            # TODO: IMPLEMENT LATER
            # await transaction.organization.create(
            #     data={
            #         "name": data.org_name.lower(),
            #         "email": data.org_email.lower(),
            #         "vatNumber": data.org_vatNumber,
            #         "address": data.org_address,
            #         "city": data.org_city,
            #         "zipCode": str(data.org_zipCode),
            #         "country": data.org_country or "Italia",
            #         "sdi": data.org_sdi,
            #         "pec": data.org_pec,
            #         "owner": {"connect": {"id": user.id}},
            #         "users": {"connect": {"id": user.id}},
            #     }
            # )

    except Exception as e:
        # Se si verifica un errore, tutte le operazioni nella transazione verranno annullate
        print(f"Si è verificato un errore: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    try:    
        _send_confirmation_email(user, confirmation_otp)
    except Exception as e:
        print(f"Error sending confirmation email: {e}")
    
    return user


@auth_router.post("/confirm")
async def confirm_account(
    data: Annotated[ConfirmAccountDto, Body(embed=True, strict=True)],
):
    try:
        user = await prisma.user.find_unique(
            where={"email": data.email}, include={"organization": True}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.confirmation_token != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        await prisma.user.update(
            where={"id": user.id}, data={"confirmed": True, "confirmation_token": None}
        )

        _create_customer_lago(user)

    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return "ok"


@auth_router.post("/resend_code")
async def resend_code(
    data: Annotated[ResendOTPDto, Body(embed=True, strict=True)],
):
    try:
        user = await prisma.user.find_unique(
            where={"email": data.email}, include={"organization": True}
        )
        if not user or not user.confirmation_token:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            return _send_confirmation_email(user, user.confirmation_token)
        except Exception as e:
            print(f"Error sending confirmation email: {e}")
            raise HTTPException(
                status_code=500, detail="Error sending confirmation email"
            )
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@auth_router.post("/sign-in")
async def sign_in(
    data: Annotated[SignInDto, Body(embed=True, strict=True)],
) -> SignInOutput:
    """# SUMMARY

    Args:
        data (Annotated[SignInDto, Body, optional): _description_. Defaults to True, strict=True)].

    Raises:
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        SignInOutput: _description_
    """
    user = await prisma.user.find_unique(where={"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.blocked:
        raise HTTPException(status_code=500, detail="User is blocked")
    elif not user.confirmed:
        raise HTTPException(status_code=500, detail="User is not confirmed")

    # Check if user is OAuth user (no password)
    if user.auth_provider != "EMAIL" and not user.password:
        provider_name = user.auth_provider.lower().capitalize()
        raise HTTPException(
            status_code=400,
            detail=f"This account uses {provider_name} sign-in. Please use {provider_name} authentication.",
        )

    if not user.password or not _check_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    jwt = auth.create_access_token(user.id)
    output = SignInOutput(jwt=jwt, is_first_login=user.first_login)

    return output


@auth_router.post("/complete-account")
async def complete_account(
    data: Annotated[CompanyInfo, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required),
):
    try:
        team_created = create_team(data.companyName, payload.sub)
        if not team_created.team_id:
            raise HTTPException(status_code=502, detail="Cannot create team")

        key_created = create_key(team_id=team_created.model_dump()["team_id"])

        await prisma.organization.create(
            data={
                "name": data.companyName,
                "email": data.companyEmail,
                "address": data.companyAddress,
                "city": data.companyCity,
                "country": "Italia",  # TODO: Add dynamic country
                "zipCode": data.companyZip,
                "goals": data.companyGoals,
                "longTermGoals": data.companyLongTermGoals,
                "vatNumber": data.companyVat,
                "sdi": data.companySdi,
                "fiscalCode": data.companyFiscalCode,
                "mission": data.companyMission,
                "vision": data.companyVision,
                "productType": data.companyProducts,
                "income": data.companyIncome,
                "owner": {"connect": {"id": payload.sub}},
                "team_key": key_created.key,
            }
        )

        await prisma.user.update(
            where={"id": payload.sub},
            data={"name": data.name, "surname": data.surname, "first_login": False},
        )

        # TODO: Run Agent
    except HTTPException as e:
        print(e)
        raise e

    return "completed"


@auth_router.get("/me")
async def get_me(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required),
) -> MeOutput:
    user = await prisma.user.find_unique(where={"id": payload.sub})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.verified_email:
        raise HTTPException(status_code=400, detail="Email not verified") 

    me = MeOutput(
        id=user.id,
        name=user.name if user.name else None,
        surname=user.surname if user.surname else None,
        email=user.email,
        is_first_login=user.first_login,
    )

    return me


@auth_router.get("/my-organization")
async def get_my_organization(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required),
) -> MyCompanyOutput:
    organization = await prisma.organization.find_first_or_raise(
        where={"users": {"some": {"id": payload.sub}}}
    )
    if not organization:
        raise HTTPException(status_code=404, detail="User not found")

    organization = MyCompanyOutput(
        id=organization.id,
        name=organization.name,
        address=organization.address,
        city=organization.city,
        zipCode=organization.zipCode,
        country=organization.country,
        sdi=organization.sdi,
        pec=organization.pec,
        email=organization.email,
        vatNumber=organization.vatNumber,
    )

    return organization


################ PRIVATE #############
async def _check_user_exist(email: EmailStr):
    user = await prisma.user.find_unique(where={"email": email})
    return True if user is not None else False


def _validate_input(data: SignUpDto):
    password_regex = (
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*)(+=._-])(?=.{8,32})"
    )

    if not data.mandatoryPrivacy:
        raise HTTPException(status_code=400, detail="You must accept privacy policy")
    elif not data.terms:
        raise HTTPException(
            status_code=400, detail="You must accept terms and conditions"
        )
    elif not re.match(password_regex, data.password):
        raise HTTPException(
            status_code=400, detail="Password does not meet the requirements"
        )

    return True


def _get_hashed_password(plain_text_password: str):
    # Hash a password for the first time
    #   (Using bcrypt, the salt is saved into the hash itself)
    hashed = bcrypt.hashpw(plain_text_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _check_password(plain_text_password: str, hashed_password: str):
    # Check hashed password. Using bcrypt, the salt is saved into the hash itself
    return bcrypt.checkpw(
        plain_text_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def _send_confirmation_email(user: User, confirmation_token: str):
    email_params = EmailParams(
        subject="Benvenuto su ReQurv AI",
        body=f"Inserisci questo codice di verifica per confermare il tuo account: {confirmation_token}",
        to_email=user.email,
        from_email="noreply@requrv.ai",
    )

    send_email(email_params)



def _create_customer_lago(user: User):
    billing_configuration = CustomerBillingConfiguration(
        invoice_grace_period=5,
        document_locale="it",
        payment_provider="stripe",
        sync=True,
        sync_with_provider=True,
        payment_provider_code=None,
        provider_customer_id=None,
        provider_payment_methods=[
            "card",
            "sepa_debit",
        ],
    )
    customer = Customer(
        firstname=user.name,
        lastname=user.surname,
        name=None,
        external_id=user.id,
        legal_name=user.organization.name if user.organization else user.name,
        country="IT",
        currency="EUR",
        email=user.organization.email if user.organization else user.email,
        address_line1=user.organization.address if user.organization else "",
        address_line2=None,
        billing_configuration=billing_configuration,
        customer_type="company",
        billing_entity_code=None,
        city=user.organization.city if user.organization else None,
        finalize_zero_amount_invoice="finalize",
        integration_customers=None,
        logo_url=None,
        invoice_custom_section_codes=None,
        legal_number=user.organization.vatNumber if user.organization else None,
        phone=None,
        metadata=None,
        net_payment_term=10,
        shipping_address=None,
        skip_invoice_custom_sections=False,
        state="IT",
        timezone="Europe/Rome",
        url=None,
        tax_codes=None,
        tax_identification_number=(
            user.organization.vatNumber if user.organization else None
        ),
        zipcode=user.organization.zipCode if user.organization else None,
    )
    create_customer(customer=customer)
