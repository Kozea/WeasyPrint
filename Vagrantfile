# -*- mode: ruby -*-
# vi: set ft=ruby :

# To use this, install Vagrant from http://vagrantup.com/ and VirtualBox
# then run 'vagrant up'

# It should automatically download an Ubuntu 10.04 virtual machine,
# install WeasyPrint with PyGTK in it and run the test suite.
# The point is to test that everything works fine with an older distribution.

# To only run the test suite later, use
# vagrant ssh -c '~/venv/bin/py.test /vagrant/weasyprint'


Vagrant::Config.run do |config|
  config.vm.box = "weasyprint-lucid32"
  config.vm.box_url = "http://files.vagrantup.com/lucid32.box"
  config.vm.provision :shell, :inline => <<-EOF
    export DEBIAN_FRONTEND=noninteractive
    apt-get update --force-yes -y
    apt-get install --force-yes -y --no-install-recommends \
        imagemagick python-lxml python-gtk2 python-virtualenv python-dev
    sudo -u vagrant -s '
        cd ~vagrant
        virtualenv venv
        # The project root directory is mounted at /vagrant
        venv/bin/pip install pytest -e /vagrant
        venv/bin/py.test /vagrant/weasyprint
    '
  EOF
end
