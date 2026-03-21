// declare socket and open websocket connection with connect function
let socket;

// websocket connect function declaration
function connect(onMessage) {
    socket = new WebSocket('ws://192.168.68.61:8080');

    // check for succesful connection and print in console
    socket.addEventListener('open', function() {
        console.log('Connected to server!');
    });
    // listen for error and print to console
    socket.addEventListener('error', function(error) {
        console.log('WebSocket error:', error);
    });

    // check for connection drop and attempt to reconnect
    socket.addEventListener('close', function() {
        console.log('Connection lost. Reconnecting...');
        connect(onMessage);
    });

    // if an onMessage callback is provided, set it as the message event listener
    if (onMessage) {
        socket.addEventListener('message', onMessage);
    }
}