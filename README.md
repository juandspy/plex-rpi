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

## Docker compose

Just run it with `docker-compose up`. Add the `-d` argument for running in
the background. You may need to modify the [.env](.env) with your paths.

### Samba

You can configure Samba in another machine using Nautilus for example. Just
connect to `smb://{RASPBERRY_IP}`. You can then browse the files in the `media`
and `downloads` folders.

### Plex

The first time you spin up the container, you may need to access 
`http://{RASPBERRY_IP}:32400/manage` to configure the server. You may need to
reload the page as sometimes it hangs.

### Transmission

The [settings.json](transmission/settings.json) is configured with password
`123456`. So visit `http://{RASPBERRY_IP}:9091` and log in with `admin/123456`.
This will launch the Transmission UI, where you can see the torrents being
download, edit the [settings.json](transmission/settings.json) using the UI and
so on.

You can try adding some torrent there and check it is correctly stored in
`${STORAGE}/torrents`.

```
juan@raspberrypi:~/plex-rpi $ ls "$STORAGE/torrents/complete"
'Big Buck Bunny (2008).mp4'
juan@raspberrypi:~/plex-rpi $ ls "$STORAGE/torrents/incomplete"
```

### Flexget

You can force Flexget to refresh the folder (otherwise it will wait for 30
minutes -or the value configured in [config.yml](flexget/config.yml)-) by using:

```
docker-compose exec flexget flexget execute --dump --tasks sort_movies
```

In order to change the Flexget password, you need to run:
```
docker-compose exec flexget flexget web passwd {YOUR_PASSWORD}
```

You can log into the UI (`http://{RASPBERRY_IP}:5050`) by introducing this password then.
