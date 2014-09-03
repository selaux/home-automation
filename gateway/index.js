'use strict';

var crypto = require('crypto'),
    config = require('./config.json'),
    radio = require('nrf').connect(config.radio.spiDev, config.radio.cePin, config.radio.irqPin);

function decryptPacket(data) {
    var i,
        dec,
        decipher = crypto.createDecipher('aes-128-ecb', new Buffer(config.preSharedKey));

    for (i = 0; i < 16; i++) {
        data[i+16] = data[i+16] ^ data[i];
    }

    decipher.setAutoPadding(false);
    dec = decipher.update(data);

    return dec;
}

radio.channel(0x4c).dataRate('1Mbps').crcBytes(2).autoRetransmit({count: 10, delay: 25});
radio.begin(function () {
    var rx = radio.openPipe('rx', parseInt(config.radio.listen, 16), { size: 32 });
    console.log('Ready to receive');
    radio.printDetails();
    rx.on('data', function (data) {
        var decrypted;
        // WORKAROUND: https://github.com/natevw/node-nrf/issues/3
        Array.prototype.reverse.call(data);

        decrypted = decryptPacket(data);
        console.log(decrypted.length);
//        console.log(decrypted);
        var str = '';
        for (var i = 0; i < 16; i++) {
            str += decrypted.readUInt8(i) + ' ';
        }
        console.log(str);
    });
});
