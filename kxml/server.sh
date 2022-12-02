#Запуск/Остановка/Перезагрузка uwsgi с доп. параметрами

name="kxml" #Название проекта
cuser=nitex #Пользователь под которым запускать воркеры/процессы uwsgi
ROOT="/home/nitex/kaskadxml/$name" #Путь до проекта
pidfile="$ROOT/logs/$name.pid"
config="configs/kxml_uwsgi.ini" # Название конфигурационного ini файла
sockets=$ROOT"/sockets"
cd $ROOT
case "$1" in
        "start")
            sudo chmod o+w $sockets
            sudo su - $cuser -c "uwsgi --ini $ROOT/$config" -s /bin/sh
        ;;
        "stop")
            sudo su - $cuser -c "uwsgi --stop $pidfile" -s /bin/sh
        ;;
        "restart")
            ./server.sh stop
            ./server.sh start
        ;;
        *)
            echo "Usage: ./server.sh {start|stop|restart}"
        ;;
esac