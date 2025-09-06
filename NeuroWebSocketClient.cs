using System;
using System.Collections;
using UnityEngine;
using System.Net.WebSockets;
using System.Threading;
using System.Text;
using Newtonsoft.Json;
using Cysharp.Threading.Tasks;

namespace ChatdollKit.LLM.Neuro
{
    [System.Serializable]
    public class WebSocketMessage
    {
        public string type;
        public string text;
        public string message;
        public float timestamp;
    }

    public class NeuroWebSocketClient : MonoBehaviour
    {
        [Header("WebSocket Configuration")]
        public string WebSocketUrl = "ws://localhost:8006";
        public bool AutoConnect = true;
        public bool AutoReconnect = true;
        public float ReconnectDelay = 5.0f;
        public float HeartbeatInterval = 30.0f; // Send ping every 30 seconds
        public bool DebugMode = true;
        
        [Header("Integration")]
        public GameObject DialogProcessor; // ChatdollKit DialogProcessor 연결
        
        [Header("Testing")]
        public bool SendTestOnConnect = false;
        [TextArea(2, 4)]
        public string TestMessage = "Hello from Unity! This is a test message.";
        
        private ClientWebSocket webSocket;
        private bool isConnected = false;
        private CancellationTokenSource cancellationTokenSource;
        private bool shouldReconnect = false;
        
        // Events
        public event Action<string> OnNeuroResponse;
        public event Action OnConnected;
        public event Action OnDisconnected;
        
        void Start()
        {
            if (AutoConnect)
            {
                shouldReconnect = AutoReconnect;
                ConnectToNeuro();
            }
        }
        
        public async void ConnectToNeuro()
        {
            try
            {
                if (DebugMode)
                    Debug.Log($"[NEURO WS] Connecting to {WebSocketUrl}");
                
                cancellationTokenSource = new CancellationTokenSource();
                webSocket = new ClientWebSocket();
                
                var uri = new Uri(WebSocketUrl);
                await webSocket.ConnectAsync(uri, cancellationTokenSource.Token);
                
                isConnected = true;
                if (DebugMode)
                    Debug.Log("[NEURO WS] Connected to Neuro WebSocket server");
                OnConnected?.Invoke();
                
                // Send test message if enabled
                if (SendTestOnConnect && !string.IsNullOrEmpty(TestMessage))
                {
                    SendChatToNeuro(TestMessage);
                    if (DebugMode)
                        Debug.Log("[NEURO WS] Auto-sent test message");
                }
                
                // Start listening for messages
                StartCoroutine(ListenForMessages());
                
                // Start heartbeat
                if (HeartbeatInterval > 0)
                {
                    StartCoroutine(HeartbeatCoroutine());
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[NEURO WS] Connection failed: {e.Message}");
                isConnected = false;
                
                // Auto-reconnect on connection failure
                if (shouldReconnect && AutoReconnect)
                {
                    StartCoroutine(AttemptReconnect());
                }
            }
        }
        
        private IEnumerator ListenForMessages()
        {
            var buffer = new byte[8192]; // Increased buffer size
            
            while (isConnected && webSocket.State == WebSocketState.Open)
            {
                var result = webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationTokenSource.Token);
                
                // Wait for async operation to complete with timeout
                float timeout = 30f;
                float elapsed = 0f;
                while (!result.IsCompleted && elapsed < timeout)
                {
                    elapsed += Time.deltaTime;
                    yield return null;
                }
                
                if (!result.IsCompleted)
                {
                    Debug.LogWarning("[NEURO WS] Receive timeout, connection may be dead");
                    break;
                }
                
                try
                {
                    var wsResult = result.Result;
                    
                    if (wsResult.MessageType == WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, wsResult.Count);
                        
                        if (DebugMode)
                            Debug.Log($"[NEURO WS] Received: {message}");
                        
                        try
                        {
                            var wsMessage = JsonConvert.DeserializeObject<WebSocketMessage>(message);
                            ProcessNeuroMessage(wsMessage);
                        }
                        catch (Exception ex)
                        {
                            Debug.LogError($"[NEURO WS] Error parsing message: {ex.Message}");
                        }
                    }
                    else if (wsResult.MessageType == WebSocketMessageType.Close)
                    {
                        Debug.Log("[NEURO WS] Server closed connection");
                        break;
                    }
                    else if (wsResult.MessageType == WebSocketMessageType.Binary)
                    {
                        if (DebugMode)
                            Debug.Log("[NEURO WS] Binary message received (possibly pong)");
                    }
                }
                catch (OperationCanceledException)
                {
                    Debug.LogWarning("[NEURO WS] Operation was cancelled");
                    break;
                }
                catch (WebSocketException e)
                {
                    Debug.LogError($"[NEURO WS] WebSocket error: {e.Message}");
                    break;
                }
                catch (Exception e)
                {
                    Debug.LogError($"[NEURO WS] Error receiving message: {e.Message}");
                    break;
                }
                
                // Small delay to prevent tight loop
                yield return new WaitForSeconds(0.01f);
            }
            
            isConnected = false;
            OnDisconnected?.Invoke();
            
            if (DebugMode)
                Debug.Log("[NEURO WS] Connection closed");
            
            // Auto-reconnect if enabled
            if (shouldReconnect && AutoReconnect)
            {
                StartCoroutine(AttemptReconnect());
            }
        }
        
        private IEnumerator AttemptReconnect()
        {
            if (DebugMode)
                Debug.Log($"[NEURO WS] Attempting reconnect in {ReconnectDelay} seconds...");
            
            yield return new WaitForSeconds(ReconnectDelay);
            
            if (!isConnected && shouldReconnect)
            {
                if (DebugMode)
                    Debug.Log("[NEURO WS] Reconnecting...");
                ConnectToNeuro();
            }
        }
        
        private void ProcessNeuroMessage(WebSocketMessage message)
        {
            switch (message.type)
            {
                case "connected":
                    if (DebugMode)
                        Debug.Log($"[NEURO WS] Server says: {message.message}");
                    break;
                    
                case "neuro_response":
                    if (DebugMode)
                        Debug.Log($"[NEURO WS] Neuro response: {message.text}");
                    
                    // Trigger DialogProcessor immediately
                    ProcessNeuroResponse(message.text);
                    OnNeuroResponse?.Invoke(message.text);
                    break;
                    
                case "ai_response":
                    if (DebugMode)
                        Debug.Log($"[NEURO WS] AI response: {message.text}");
                    
                    ProcessNeuroResponse(message.text);
                    OnNeuroResponse?.Invoke(message.text);
                    break;
                
                case "pong":
                case "heartbeat_response":
                    if (DebugMode)
                        Debug.Log("[NEURO WS] Heartbeat response received");
                    break;
                    
                default:
                    if (DebugMode)
                        Debug.Log($"[NEURO WS] Unknown message type: {message.type}");
                    break;
            }
        }
        
        private void ProcessNeuroResponse(string responseText)
        {
            // Send to DialogProcessor or ChatdollKit immediately
            if (DialogProcessor != null)
            {
                // Find ChatdollKit DialogProcessor component
                var processor = DialogProcessor.GetComponent<ChatdollKit.Dialog.DialogProcessor>();
                if (processor != null)
                {
                    StartCoroutine(SendToDialogProcessor(processor, responseText));
                }
                else
                {
                    Debug.LogWarning("[NEURO WS] DialogProcessor component not found");
                }
            }
            else
            {
                Debug.LogWarning("[NEURO WS] DialogProcessor GameObject not assigned");
            }
        }
        
        private IEnumerator SendToDialogProcessor(ChatdollKit.Dialog.DialogProcessor processor, string text)
        {
            // Start dialog processing without waiting (fire and forget)
            var task = processor.StartDialogAsync(text);
            
            // Wait for completion
            while (task.Status != UniTaskStatus.Succeeded && 
                   task.Status != UniTaskStatus.Faulted && 
                   task.Status != UniTaskStatus.Canceled)
            {
                yield return null;
            }
            
            if (task.Status == UniTaskStatus.Faulted)
            {
                Debug.LogError($"[NEURO WS] Error sending to DialogProcessor");
            }
            else if (DebugMode)
            {
                Debug.Log($"[NEURO WS] Sent to DialogProcessor: {text}");
            }
        }
        
        public async void SendChatToNeuro(string message)
        {
            if (isConnected && webSocket != null && webSocket.State == WebSocketState.Open)
            {
                var chatMessage = new
                {
                    type = "chat",
                    text = message,
                    user_id = "unity_user",
                    timestamp = Time.time
                };
                
                string jsonMessage = JsonConvert.SerializeObject(chatMessage);
                byte[] bytes = Encoding.UTF8.GetBytes(jsonMessage);
                
                await webSocket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellationTokenSource.Token);
                
                if (DebugMode)
                    Debug.Log($"[NEURO WS] Sent to Neuro: {message}");
            }
            else
            {
                Debug.LogWarning("[NEURO WS] WebSocket not connected");
            }
        }
        
        public bool IsConnected()
        {
            return isConnected && webSocket != null && webSocket.State == WebSocketState.Open;
        }
        
        public void StopReconnecting()
        {
            shouldReconnect = false;
            if (DebugMode)
                Debug.Log("[NEURO WS] Auto-reconnect disabled");
        }
        
        private IEnumerator HeartbeatCoroutine()
        {
            while (isConnected && webSocket != null && webSocket.State == WebSocketState.Open)
            {
                yield return new WaitForSeconds(HeartbeatInterval);
                
                if (isConnected && webSocket != null && webSocket.State == WebSocketState.Open)
                {
                    try
                    {
                        // Send heartbeat message as JSON
                        var heartbeatMessage = new
                        {
                            type = "heartbeat",
                            timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
                        };
                        
                        string jsonMessage = JsonConvert.SerializeObject(heartbeatMessage);
                        byte[] bytes = Encoding.UTF8.GetBytes(jsonMessage);
                        
                        // Send async without waiting
                        _ = webSocket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellationTokenSource.Token);
                        
                        if (DebugMode)
                            Debug.Log("[NEURO WS] Sent heartbeat ping");
                    }
                    catch (Exception e)
                    {
                        Debug.LogWarning($"[NEURO WS] Failed to send heartbeat: {e.Message}");
                        // Connection might be dead
                        isConnected = false;
                        break;
                    }
                }
            }
        }
        
        void OnDestroy()
        {
            shouldReconnect = false; // Stop reconnection attempts
            
            if (webSocket != null)
            {
                if (webSocket.State == WebSocketState.Open)
                {
                    webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Unity closing", CancellationToken.None);
                }
                webSocket.Dispose();
                webSocket = null;
            }
            
            if (cancellationTokenSource != null)
            {
                cancellationTokenSource.Cancel();
                cancellationTokenSource.Dispose();
            }
        }
        
        // Inspector methods for testing
        [ContextMenu("Test Connection")]
        public void TestConnection()
        {
            if (IsConnected())
            {
                Debug.Log("✅ WebSocket is connected and ready");
            }
            else
            {
                Debug.LogWarning("❌ WebSocket not connected");
            }
        }
        
        [ContextMenu("Send Test Message")]
        public void SendTestMessage()
        {
            if (IsConnected())
            {
                SendChatToNeuro(TestMessage);
                Debug.Log($"📤 Sent test message: {TestMessage}");
            }
            else
            {
                Debug.LogWarning("❌ Cannot send - WebSocket not connected");
            }
        }
        
        [ContextMenu("Reconnect")]
        public async void Reconnect()
        {
            if (webSocket != null)
            {
                if (webSocket.State == WebSocketState.Open)
                {
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Reconnecting", CancellationToken.None);
                }
                webSocket.Dispose();
            }
            
            if (cancellationTokenSource != null)
            {
                cancellationTokenSource.Cancel();
                cancellationTokenSource.Dispose();
            }
            
            ConnectToNeuro();
        }
    }
}