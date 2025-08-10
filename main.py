import motor.motor_asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler
import os

# MongoDB Setup
MONGO_URL = os.getenv("MONGO_URL")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
database = client.books_db  # <- Переименовано
books_collection = database.get_collection('books')
print('\n> MongoDB connection - OK\n')

# Custom ObjectId for Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid ObjectId')
        return ObjectId(v)

    def __str__(self):
        return str(self)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str)
        )

# Pydantic Models
class BookBase(BaseModel):
    title: str
    author: str
    year: int
   

class BookCreate(BookBase):
    pass

class BookInDB(BookBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "title": "It clown",
                "author": "Stephen King",
                "year": 1951,
          
                "id": "examplebookid123456"
            }
        }

# FastAPI app setup
app = FastAPI()

origins = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://host.docker.internal:5173',
    'https://bookbackend-ruye.onrender.com',
    'https://bookfrontend-x2ez.onrender.com'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get('/')
async def hello():
    return {'message': 'Hello from FastAPI'}

# Routes
@app.post('/books/', response_model=BookInDB, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate):
    book_dict = book.model_dump(by_alias=True)
    result = await books_collection.insert_one(book_dict)
    new_book = await books_collection.find_one({'_id': result.inserted_id})
    processed = dict(new_book)
    processed['_id'] = str(processed['_id'])
    return BookInDB(**processed)

@app.get('/books/', response_model=List[BookInDB])
async def read_books(skip: int = 0, limit: int = 10):
    books = []
    async for book in books_collection.find().skip(skip).limit(limit):
        processed = dict(book)
        processed['_id'] = str(processed['_id'])
        books.append(BookInDB(**processed))
    return books

@app.get('/books/{book_id}', response_model=BookInDB)
async def read_book(book_id: str):
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail='Invalid Book ID')
    book = await books_collection.find_one({'_id': ObjectId(book_id)})
    if book:
        processed = dict(book)
        processed['_id'] = str(processed['_id'])
        return BookInDB(**processed)
    raise HTTPException(status_code=404, detail='Book Not Found')

@app.put('/books/{book_id}', response_model=BookInDB)
async def update_book(book_id: str, book: BookCreate):
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail='Invalid Book ID')

    update_result = await books_collection.update_one(
        {'_id': ObjectId(book_id)},
        {'$set': book.dict()}
    )

    if update_result.modified_count == 1:
        updated = await books_collection.find_one({'_id': ObjectId(book_id)})
        processed = dict(updated)
        processed['_id'] = str(processed['_id'])
        return BookInDB(**processed)

    existing = await books_collection.find_one({'_id': ObjectId(book_id)})
    if existing:
        processed = dict(existing)
        processed['_id'] = str(processed['_id'])
        return BookInDB(**processed)

    raise HTTPException(status_code=404, detail='Book Not Found')

@app.delete('/books/{book_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: str):
    if not ObjectId.is_valid(book_id):
        raise HTTPException(status_code=400, detail='Invalid Book ID')

    delete_result = await books_collection.delete_one({'_id': ObjectId(book_id)})

    if delete_result.deleted_count == 1:
        return {'message': 'Book deleted successfully'}

    raise HTTPException(status_code=404, detail='Book Not Found')
