#використовувати оффіційний образ пайтона:
FROM python:3.11-slim-buster

#визначаєм робочу дерикторію
WORKDIR /app
#копіюєм файл із залежностями
 COPY requirements.txt .

 #Інасталюємо залежності до контейнера
RUN pip install --no-cache-dir -r requirements.txt

#Копіюємо весь код додатку до контейнера:
COPY . .
# Відкриваємо порт,на якому працює сервер FASTAPI
EXPOSE 8000
#Запускаємл FASTAPI за допомогою асихроного сервера UVIcorn:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 