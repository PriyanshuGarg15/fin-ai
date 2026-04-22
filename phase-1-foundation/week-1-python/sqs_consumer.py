# PYTHON → NODE.JS MENTAL MODEL MAPPING
# asyncio.gather()     → Promise.all()
# async/await          → async/await (same syntax)
# asyncio.Semaphore()  → p-limit or bottleneck library
# async with          → using statement / try-finally with cleanup
# asyncio.run()        → the event loop (Node runs automatically)

from dataclasses import dataclass
import asyncio
import random
import time

@dataclass
class SQSMessage:
    message_id: str
    receipt_handle: str
    body: dict
    recieve_count: int=1

class Async_Consumer:
    def __init__(self, queue_name: str, max_concurrency: int=10):
        self.queue_name=queue_name
        self.max_concurrency=max_concurrency
        self.semaphore= asyncio.Semaphore(max_concurrency)
        self.processed=0
        self.failed=0
    
    async def process_message(self, message: SQSMessage)->bool:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            if random.random() < 0.1:
                print (f"Failed to process message {message.message_id}, Sending to DLQ")
                self.failed+=1
                return False
            self.processed+=1
            return True
    
    async def recieve_message(self)->list[SQSMessage]:
        await asyncio.sleep(random.uniform(0.5, 2.0))
        return [SQSMessage(message_id=f"MESSAGE{i:04d}", receipt_handle=f"RECEIPT{i:04d}", body={"message": f"Message {i:04d}"}) for i in range(10)]
    
    async def delete_message(self, message: SQSMessage):
        await asyncio.sleep(random.uniform(0.5, 2.0))
        print(f"Deleted message {message.message_id}")
    
    async def send_to_dlq(self, message: SQSMessage):
        await asyncio.sleep(random.uniform(0.5, 2.0))
        print(f"Sent message {message.message_id} to DLQ")
    
    async def run_once(self):
        messages= await self.recieve_message()
        tasks=[]
        for msg in messages:
            # print(f"Processing message {msg.message_id}")
            tasks.append(self.handle_message(msg))
        await asyncio.gather(*tasks)

    async def handle_message(self, message: SQSMessage):
        print(f"Processing message {message.message_id}")
        if await self.process_message(message):
            await self.delete_message(message)
        else:
            await self.send_to_dlq(message)
        
async def main():
    consumer= Async_Consumer("my-queue",max_concurrency=7)
    start=time.perf_counter()
    await consumer.run_once()
    print(f"Processed {consumer.processed} messages in {time.perf_counter()-start:0.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
