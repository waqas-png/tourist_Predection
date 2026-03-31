from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    log_tourism_receipts:     float = Field(..., example=20.5,  description="log(tourism_receipts + 1)")
    log_tourism_exports:      float = Field(..., example=3.2,   description="log(tourism_exports + 1)")
    log_tourism_expenditures: float = Field(..., example=18.9,  description="log(tourism_expenditures + 1)")
    log_gdp:                  float = Field(..., example=26.1,  description="log(GDP + 1)")
    inflation:                float = Field(..., example=2.5,   description="Annual inflation rate (%)")
    year_norm:                float = Field(..., example=0.85,  description="Year normalised 0–1 (1999=0, 2023=1)")
    is_post_covid:            int   = Field(..., example=0,     description="1 if year >= 2020 else 0")
    decade:                   int   = Field(..., example=2010,  description="Decade bucket (2000/2010/2020)")
    lag1_log_arrivals:        float = Field(..., example=15.2,  description="log arrivals of previous year")
    lag2_log_arrivals:        float = Field(..., example=15.0,  description="log arrivals 2 years ago")
    arrival_growth:           float = Field(..., example=0.05,  description="YoY growth in log arrivals")
    country_enc:              int   = Field(..., example=42,    description="Label-encoded country ID")

    class Config:
        json_schema_extra = {
            "example": {
                "log_tourism_receipts": 20.5,
                "log_tourism_exports": 3.2,
                "log_tourism_expenditures": 18.9,
                "log_gdp": 26.1,
                "inflation": 2.5,
                "year_norm": 0.85,
                "is_post_covid": 0,
                "decade": 2010,
                "lag1_log_arrivals": 15.2,
                "lag2_log_arrivals": 15.0,
                "arrival_growth": 0.05,
                "country_enc": 42,
            }
        }


class PredictionResponse(BaseModel):
    log_prediction:    float = Field(..., description="Predicted log(arrivals + 1)")
    predicted_arrivals: int  = Field(..., description="Predicted actual tourism arrivals count")
