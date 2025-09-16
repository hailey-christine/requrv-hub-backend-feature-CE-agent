import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from authx import TokenPayload
from core.settings import auth
from core.services.prisma import prisma
from prisma.models import User, Organization 
from prisma.enums import AccountType, TypeChartAccount
from core.modules.media.service import upload_file_to_s3
import pandas

async def upload_comparison_file_service(
    user_id: str,
    year: int,
    file: UploadFile = File(...)
):
    user: User = await prisma.user.find_unique(where={"id": user_id}, include={"owner": True})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")   
    # Qui salvo il file sul bucket e sul db e lo processo

    organizationId: Organization = await prisma.organization.find_unique(where={"id": user.organizationId if user.organizationId else user.owner.id}, include={"incomeStatementConversionTable": True})

    if not organizationId:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Questa parte serve per avere un solo file ma con delle piccole modifiche si potrebbe permettere di avere più file, ma come stabilito ora si usa soltanto uno
    if organizationId.incomeStatementConversionTable:
        raise HTTPException(status_code=400, detail=f"Income Statement Conversion Table already exists")

    try:
        media = await upload_file_to_s3(file, who_uploaded_it_user_id=user.id)
    except Exception as e:
        logging.error("Error uploading file to S3: %s", e)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    
        
    if file.content_type == "text/csv":
        df = pandas.read_csv(file.file)
    elif file.content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        df = pandas.read_excel(file.file)

    chart_accounts_cee_to_create: set = []
    chart_accounts_to_create = []   
    
    for index, row in df.iterrows():
        chart_account_code = str(row.get("Conto")).strip() if row.get("Conto") else None
        chart_account_description = str(row.get("Descrizione Conto")).strip() if row.get("Descrizione Conto") else None
        chart_account_type = str(row.get("Tipo")).strip().upper() if row.get("Tipo") else None
        chart_account_account_type = str(row.get("Valorizzazione")).strip().upper() if row.get("Valorizzazione") else None
        chart_account_code_debit_cee = str(row.get("DARE Voce")).strip() if row.get("DARE Voce") else None
        chart_account_description_debit_cee = str(row.get("Descrizione_DARE")).strip() if row.get("Descrizione_DARE") else None
        chart_account_code_credit_cee = str(row.get("AVERE Voce")).strip() if row.get("AVERE Voce") else None
        chart_account_description_credit_cee = str(row.get("Descrizione_AVERE")).strip() if row.get("Descrizione_AVERE") else None
 
        
        if chart_account_code_debit_cee not in [item["code"] for item in chart_accounts_cee_to_create]:
            chart_accounts_cee_to_create.append({
                "code": chart_account_code_debit_cee,
                "description": chart_account_description_debit_cee
            })
        if chart_account_code_credit_cee not in [item["code"] for item in chart_accounts_cee_to_create]:
            chart_accounts_cee_to_create.append({
                "code": chart_account_code_credit_cee,
                "description": chart_account_description_credit_cee
            })
        
        if chart_account_code not in [item["code"] for item in chart_accounts_to_create]:
            mapped_type = _map_chart_account_type(chart_account_account_type)
            mapped_account_type = _map_account_type(chart_account_type)

            if (not chart_account_code_debit_cee and not chart_account_code_credit_cee ) or ( chart_account_code_debit_cee == "nan" and chart_account_code_credit_cee == "nan"):
                chart_accounts_to_create.append({
                    "code": chart_account_code,
                    "description": chart_account_description,
                    "type": mapped_type,
                    "accountType": mapped_account_type,
                    "toConsider": False,  # Impostato a False quando non ci sono codici CEE
                    "chart_account_code_debit_cee": None,
                    "chart_account_code_credit_cee": None
                })
            else: 
                chart_accounts_to_create.append({
                    "code": chart_account_code,
                    "description": chart_account_description,
                    "type": mapped_type,
                    "accountType": mapped_account_type,
                    "toConsider": True,
                    "chart_account_code_debit_cee": chart_account_code_debit_cee,
                    "chart_account_code_credit_cee": chart_account_code_credit_cee
                })

    
    try: 
        async with prisma.tx() as transaction:
            incomeStatementConversionTable = await transaction.incomestatementconversiontable.create(
                data={
                    "years": [year],
                    "organizationId": user.organizationId if user.organizationId else user.owner.id,
                    "mediaId": media.id,
                }
            )

            # qui cerco i chart account cee che esistono già e li toglio da quelli da creare
            existing_chart_accounts_cee = await transaction.chartaccountcee.find_many(
                where={
                    "OR": [
                        {"code": {"in": [item["code"] for item in chart_accounts_cee_to_create]}}
                    ]
                }
            )
            chart_accounts_cee_to_create = [item for item in chart_accounts_cee_to_create if item["code"] not in [cee.code for cee in existing_chart_accounts_cee]]

            await transaction.chartaccountcee.create_many(
                data=chart_accounts_cee_to_create,
                skip_duplicates=True
            )

            chart_accounts_cee_created = await transaction.chartaccountcee.find_many(
                where={
                    "OR": [
                        {"code": {"in": [item["code"] for item in chart_accounts_cee_to_create]}}
                    ]
                }
            )

        

            await transaction.chartaccount.create_many(
                data=[
                    {
                        "code": item["code"],
                        "description": item["description"],
                        "type": item["type"],
                        "accountType": item["accountType"],
                        "toConsider": item["toConsider"],
                        "incomeStatementConversionTableId": incomeStatementConversionTable.id,
                        "chartAccountCEEdebitId": next((cee.id for cee in chart_accounts_cee_created if cee.code == item["chart_account_code_debit_cee"]), None),
                        "chartAccountCEEcreditId": next((cee.id for cee in chart_accounts_cee_created if cee.code == item["chart_account_code_credit_cee"]), None)
                    }
                    for item in chart_accounts_to_create
                ],
                skip_duplicates=True
            )

    except Exception as e:
        logging.error("Error uploading or processing file: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
   
    return {"message": "File uploaded and processed successfully"}
    
async def get_chart_accounts_service(
    user_id: str,
    take: int, 
    number_page: int,
    include_cee: bool = False
):
    
    if number_page < 1:
        raise HTTPException(status_code=400, detail="Number Page must be greater than 0")
    if take < 0:
        raise HTTPException(status_code=400, detail="Take must be greater than or equal to 0")
    
    user: User = await prisma.user.find_unique(where={"id": user_id}, include={"owner": True})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")   
    # Qui salvo il file sul bucket e sul db e lo processo

    organizationId: str = user.organizationId if user.organizationId else user.owner.id

    if not organizationId:
        raise HTTPException(status_code=404, detail="Organization not found")
    

    total_count = await prisma.chartaccount.count(
        where={
            "incomeStatementConversionTable": {
                "organizationId": organizationId
            }
        }
    )

    chart_accounts = await prisma.chartaccount.find_many(
        where={
            "incomeStatementConversionTable": {
                "organizationId": organizationId
            },
            "toConsider": True
        },
        include=
        {
            "chartAccountCEEdebit": include_cee,
            "chartAccountCEEcredit": include_cee
        },
        skip=(number_page - 1) * take,
        take=take,
        order={
            "createdAt": "desc"
        }
    )

    return {
        "data": chart_accounts,
        "total": total_count
    }


def _map_chart_account_type(chart_account_type):
    """
    Mappa il tipo di conto dal file xlsx all'enum TypeChartAccount di Prisma
    """
    if not chart_account_type or chart_account_type == "nan":
        print("Chart account type is None or nan")
        return None
    mapping = {
        "ATTIVO": TypeChartAccount.ACTIVE,
        "PASSIVO": TypeChartAccount.PASSIVE,
        "ATTIVO/PASSIVO": TypeChartAccount.ACTIVE_PASSIVE,
        "RICAVI": TypeChartAccount.REVENUE,
        "COSTI": TypeChartAccount.COST
    }
    return mapping.get(chart_account_type)

def _map_account_type(chart_account_account_type):
    """
    Mappa il tipo di account dal file xlsx all'enum AccountType di Prisma
    """
    if not chart_account_account_type or chart_account_account_type == "nan":
        print("Account type is None or nan")
        return None
    mapping = {
        "STATO PATRIMONIALE": AccountType.BALANCE_SHEET,
        "CONTO ECONOMICO": AccountType.INCOME_STATEMENT, 
        "CONTI D'ORDINE": AccountType.MEMORANDUM_ACCOUNT
    }
    return mapping.get(chart_account_account_type) 