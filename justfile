default:
    echo "Available recipes: build, test, clean"

build:
    sudo rm -rf node_modules && .vscode/build.sh

# DECK=deck@<address of your device> just test
test:
    scp out/*.zip "${DECK:?set DECK to user@host of your device}":~/Desktop

clean:
    sudo rm -rf node_modules dist
    sudo rm -rf /tmp/decky