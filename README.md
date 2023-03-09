# Plex over Docker in Raspberry

## Installing the Raspberry Pi OS

Install the Raspberry Pi Imager in your PC and burn the Raspbian Lite OS in the
SD. If you are not in Ubuntu, Windows or Mac, you may need to build it following
the instructions in https://github.com/raspberrypi/rpi-imager.

Then enter the SD card in the Raspberry and just follow the steps for creating
a user and connecting to the Internet.

###  Set a static IP

Follow [this tutorial](https://peppe8o.com/assign-static-ip-and-manage-networking-in-raspberry-pi-os-lite/).

### Automount the external HDD

Follow [this tutorial](https://peppe8o.com/automount-usb-storage-with-raspberry-pi-os-lite-fstab-and-autofs/).
Using `autofs` is straightforward and doesn't require to install any additional 
packages. Also, if you need to format your drive, follow 
[this turorial](https://phoenixnap.com/kb/linux-format-disk).

### Install docker and docker-compose

Follow [this tutorial](https://peppe8o.com/setup-a-docker-environment-with-raspberry-pi-os-lite-and-portainer/).
You can optionally install Portainer, although it's not needed at all.

Also, set up docker to use the external drive for storing the temp files. This
way we keep the SD card safer:

```sh
echo "export DOCKER_TMPDIR=\"/media/hdd-1/docker-tmp\"" > /etc/default/docker
```

## Cómo correrlo

Simplemente bajate este repo y modificá las rutas de tus archivos en el archivo (oculto) .env, y después corré:

`docker-compose up -d`

## IMPORTANTE

Las raspberry son computadoras excelentes pero no muy potentes, y plex por defecto intenta transcodear los videos para ahorrar ancho de banda (en mi opinión, una HORRIBLE idea), y la chiquita raspberry no se aguanta este transcodeo "al vuelo", entonces hay que configurar los CLIENTES de plex (si, hay que hacerlo en cada cliente) para que intente reproducir el video en la máxima calidad posible, evitando transcodear y pasando el video derecho a tu tele o Chromecast sin procesar nada, de esta forma, yo he tenido 3 reproducciones concurrentes sin ningún problema. En android y iphone las opciones son muy similares, dejo un screenshot de Android acá:

<img src="https://i.imgur.com/F3kZ9Vh.png" alt="plex" width="400"/>

Más info acá: https://github.com/pablokbs/plex-rpi/issues/3
