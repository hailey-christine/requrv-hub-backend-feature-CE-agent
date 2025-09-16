-- CreateTable
CREATE TABLE "Webhook" (
    "id" UUID NOT NULL,
    "data" JSONB NOT NULL,
    "hasBeenProcessed" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP NOT NULL,

    CONSTRAINT "Webhook_pkey" PRIMARY KEY ("id")
);
