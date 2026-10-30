FROM python:3.12-slim  
#это чтобы просто быстрее собиралось да слим
WORKDIR /app 
#это мы сами так снова назвали, отношения к app внутри app.py не имеет, просто одноименные да
COPY requirements.txt . 
#точка обозначает скопировать в текущий файл?
RUN pip install --no-cache-dir -r requirements.txt 
#эта команда прям запускает всевсе что там написано на скачивание?
COPY app.py db.py ./ 
#почему в конце /
EXPOSE 5051 

CMD ["python", "app.py"] 
# что означают python и  app.py здесь