import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const useSocket = () => {
    const [socket, setSocket] = useState(null);

    useEffect(() => {
        // Create socket connection
        const socketConnection = io('http://localhost:5005', {
            transports: ['websocket', 'polling'],
            forceNew: true,
            reconnection: true,
            timeout: 5000,
        });

        socketConnection.on('connect', () => {
            console.log('✅ Connected to WebSocket server');
        });

        socketConnection.on('disconnect', () => {
            console.log('❌ Disconnected from WebSocket server');
        });

        socketConnection.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
        });

        setSocket(socketConnection);

        // Cleanup on unmount
        return () => {
            socketConnection.disconnect();
        };
    }, []);

    return socket;
};

export { useSocket }; 