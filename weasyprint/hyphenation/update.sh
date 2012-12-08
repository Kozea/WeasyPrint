host='http://http.us.debian.org/debian/pool/main'

for folder in 'h/hyphen' 'o/openoffice.org-dictionaries'; do
    for file in `curl -s $host/$folder/ | grep '"hyphen-' | cut -d '"' -f 2`; do
        wget -q $host/$folder/$file
        ar x $file data.tar.gz
        tar xfz data.tar.gz --no-recursion `tar tfz data.tar.gz | grep  "hyphen/hyph_.*\.dic"`
        mv usr/share/hyphen/*.dic .
        rm -rf usr
        rm data.tar.gz
        rm $file
    done
done
