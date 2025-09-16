/*
  Warnings:

  - The values [cost,revenue] on the enum `TypeChartAccount` will be removed. If these variants are still used in the database, this will fail.

*/
-- CreateEnum
CREATE TYPE "AccountType" AS ENUM ('BALANCE_SHEET', 'INCOME_STATEMENT', 'MEMORANDUM_ACCOUNT');

-- AlterEnum
BEGIN;
CREATE TYPE "TypeChartAccount_new" AS ENUM ('COST', 'REVENUE', 'ACTIVE', 'PASSIVE', 'ACTIVE_PASSIVE');
ALTER TABLE "ChartAccount" ALTER COLUMN "type" TYPE "TypeChartAccount_new" USING ("type"::text::"TypeChartAccount_new");
ALTER TYPE "TypeChartAccount" RENAME TO "TypeChartAccount_old";
ALTER TYPE "TypeChartAccount_new" RENAME TO "TypeChartAccount";
DROP TYPE "TypeChartAccount_old";
COMMIT;

-- AlterTable
ALTER TABLE "ChartAccount" ADD COLUMN     "accountType" "AccountType";
