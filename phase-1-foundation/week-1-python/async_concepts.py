import asyncio
import random
import time

async def fetch_credit_score(applicant_id: str)-> dict:
    await asyncio.sleep(random.uniform(0.5, 2.0))
    return {"applicant_id": applicant_id, "credit_score": random.randint(300, 850)}

async def fetch_all(applicant_ids: list[str])->list[dict]:
    return await asyncio.gather(*(fetch_credit_score(aid) for aid in applicant_ids))    

class asyncDBConnection:
    async def __aenter__(self):
        print("Opening DB Connection")
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("Closing DB Connection")
        await asyncio.sleep(0.1)
    
    async def execute(self, query: str)->list:
        print("Executing Query")
        await asyncio.sleep(0.1)
        return [{"id":1, "status":'active'}]
    

async def main():
    ids= [f"APPLICATNT{i:04d}" for i in range(10)]
    start = time.perf_counter()
    results= await fetch_all(ids)
    elapsed = time.perf_counter() - start
    print(f"Fetched {len(results)} credit scores. Time taken: {elapsed:0.2f} seconds")
    async with asyncDBConnection() as db:
        rows= await db.execute("SELECT * FROM table")
        print(f"Executed Query. Got {len(rows)} rows")

if __name__ == "__main__":
    asyncio.run(main())