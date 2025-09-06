using System;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;
using ChatdollKit.Dialog;
using ChatdollKit.LLM;
using ChatdollKit.LLM.Neuro;
using System.Collections.Generic;
using Cysharp.Threading.Tasks;

public static class NativeWebChatAPI
{
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern IntPtr CreateWindowEx(
        uint dwExStyle, string lpClassName, string lpWindowName, uint dwStyle,
        int x, int y, int nWidth, int nHeight, IntPtr hWndParent, IntPtr hMenu,
        IntPtr hInstance, IntPtr lpParam);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool UpdateWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool DestroyWindow(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr DefWindowProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern ushort RegisterClass(ref WNDCLASS lpWndClass);

    [DllImport("kernel32.dll")]
    public static extern IntPtr GetModuleHandle(string lpModuleName);

    [DllImport("user32.dll")]
    public static extern IntPtr LoadCursor(IntPtr hInstance, int lpCursorName);

    [DllImport("gdi32.dll")]
    public static extern IntPtr GetStockObject(int fnObject);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, string lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool SetFocus(IntPtr hWnd);

    [DllImport("gdi32.dll")]
    public static extern IntPtr CreateSolidBrush(uint color);

    [DllImport("gdi32.dll")]
    public static extern bool DeleteObject(IntPtr hObject);

    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

    [DllImport("gdi32.dll")]
    public static extern uint SetBkColor(IntPtr hdc, uint color);

    [DllImport("gdi32.dll")]
    public static extern uint SetTextColor(IntPtr hdc, uint color);

    [DllImport("user32.dll")]
    public static extern bool InvalidateRect(IntPtr hWnd, IntPtr lpRect, bool bErase);

    [DllImport("gdi32.dll")]
    public static extern IntPtr CreateFont(int nHeight, int nWidth, int nEscapement, int nOrientation,
        int fnWeight, uint fdwItalic, uint fdwUnderline, uint fdwStrikeOut, uint fdwCharSet,
        uint fdwOutputPrecision, uint fdwClipPrecision, uint fdwQuality, uint fdwPitchAndFamily,
        string lpszFace);

    [DllImport("gdi32.dll")]
    public static extern bool RoundRect(IntPtr hdc, int nLeftRect, int nTopRect, int nRightRect, int nBottomRect, int nWidth, int nHeight);

    [DllImport("gdi32.dll")]
    public static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);

    [DllImport("user32.dll")]
    public static extern bool FillRect(IntPtr hDC, ref RECT lprc, IntPtr hbr);

    [DllImport("gdi32.dll")]
    public static extern bool Rectangle(IntPtr hdc, int nLeftRect, int nTopRect, int nRightRect, int nBottomRect);

    [DllImport("user32.dll")]
    public static extern bool DrawText(IntPtr hDC, string lpchText, int nCount, ref RECT lpRect, uint uFormat);

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

    // Constants
    public const uint WS_OVERLAPPEDWINDOW = 0xCF0000;
    public const uint WS_VISIBLE = 0x10000000;
    public const uint WS_CHILD = 0x40000000;
    public const uint WS_BORDER = 0x00800000;
    public const uint ES_MULTILINE = 0x0004;
    public const uint ES_READONLY = 0x0800;
    public const uint ES_AUTOVSCROLL = 0x0040;
    public const uint WS_VSCROLL = 0x00200000;
    public const int SW_SHOW = 5;
    public const int SW_HIDE = 0;
    public const uint WM_COMMAND = 0x0111;
    public const uint WM_CLOSE = 0x0010;
    public const uint WM_DESTROY = 0x0002;
    public const uint WM_SETTEXT = 0x000C;
    public const uint WM_GETTEXT = 0x000D;
    public const uint WM_GETTEXTLENGTH = 0x000E;
    public const uint WM_PAINT = 0x000F;
    public const uint WM_ERASEBKGND = 0x0014;
    public const uint WM_SETFONT = 0x0030;
    public const uint EM_SETSEL = 0x00B1;
    public const int IDC_ARROW = 32512;
    public const int WHITE_BRUSH = 0;

    // Control IDs
    public const int ID_HEADER = 4001;
    public const int ID_CHAT_DISPLAY = 4002;
    public const int ID_CHAT_INPUT = 4003;
    public const int ID_SEND_BUTTON = 4004;
    public const int ID_STATUS = 4005;

    // Colors (RGB format: 0x00BBGGRR)
    public const uint COLOR_GRADIENT_START = 0x006B5FFF; // Pink
    public const uint COLOR_GRADIENT_END = 0x00F6823B;   // Blue
    public const uint COLOR_USER_BUBBLE = 0x006B5FFF;    // Pink
    public const uint COLOR_BOT_BUBBLE = 0x00F6823B;     // Blue
    public const uint COLOR_BACKGROUND = 0x00F5F5F5;     // Light gray
    public const uint COLOR_WHITE = 0x00FFFFFF;
    public const uint COLOR_TEXT_DARK = 0x00333333;

    // Draw Text flags
    public const uint DT_LEFT = 0x00000000;
    public const uint DT_CENTER = 0x00000001;
    public const uint DT_RIGHT = 0x00000002;
    public const uint DT_VCENTER = 0x00000004;
    public const uint DT_SINGLELINE = 0x00000020;
    public const uint DT_WORDBREAK = 0x00000010;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct WNDCLASS
    {
        public uint style;
        public WndProcDelegate lpfnWndProc;
        public int cbClsExtra;
        public int cbWndExtra;
        public IntPtr hInstance;
        public IntPtr hIcon;
        public IntPtr hCursor;
        public IntPtr hbrBackground;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string lpszMenuName;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string lpszClassName;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public delegate IntPtr WndProcDelegate(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
}

public class NativeWebChatWindow : MonoBehaviour
{
    [Header("Native Web Chat Settings")]
    public string windowTitle = "🤖 MikuBot Modern Chat";
    public int windowWidth = 400;
    public int windowHeight = 600;
    
    [Header("Component References")]
    public DialogProcessor dialogProcessor;
    public NeuroWebSocketClient neuroWebSocketClient;

    private IntPtr chatWindowHandle;
    private IntPtr headerHandle;
    private IntPtr chatDisplayHandle;
    private IntPtr chatInputHandle;
    private IntPtr sendButtonHandle;
    private IntPtr statusHandle;
    private IntPtr hInstance;
    private NativeWebChatAPI.WndProcDelegate wndProcDelegate;
    private string className = "NativeWebMikuBotChat";
    private bool isWindowCreated = false;
    private bool isCallbackSetup = false;

    private List<ChatMessage> messages = new List<ChatMessage>();
    private IntPtr pinkBrush;
    private IntPtr blueBrush;
    private IntPtr grayBrush;
    private IntPtr whiteBrush;
    private IntPtr headerFont;
    private IntPtr messageFont;

    private class ChatMessage
    {
        public string sender;
        public string content;
        public DateTime timestamp;
        public bool isUser;

        public ChatMessage(string sender, string content, bool isUser)
        {
            this.sender = sender;
            this.content = content;
            this.timestamp = DateTime.Now;
            this.isUser = isUser;
        }

        public string GetDisplayText()
        {
            string timeStr = timestamp.ToString("HH:mm");
            string emoji = isUser ? "👤" : "🤖";
            return $"{emoji} {sender} [{timeStr}]\r\n{content}\r\n";
        }
    }

    void Start()
    {
#if UNITY_EDITOR
        Debug.Log("NativeWebChatWindow: Editor mode - chat window not available");
        return;
#endif

#if UNITY_STANDALONE_WIN
        if (dialogProcessor == null)
        {
            dialogProcessor = FindObjectOfType<DialogProcessor>();
        }

        SetupDialogProcessorCallbacks();
        CreateNativeWebChatWindow();
#endif
    }

    void SetupDialogProcessorCallbacks()
    {
        if (dialogProcessor == null || isCallbackSetup) return;

        var originalCallback = dialogProcessor.OnResponseShownAsync;

        dialogProcessor.OnResponseShownAsync = async (inputText, payloads, llmSession, token) =>
        {
            try
            {
                if (originalCallback != null)
                {
                    await originalCallback(inputText, payloads, llmSession, token);
                }

                if (llmSession != null && !string.IsNullOrEmpty(llmSession.StreamBuffer))
                {
                    await UniTask.SwitchToMainThread();
                    
                    string responseText = llmSession.StreamBuffer.Trim();
                    if (!string.IsNullOrEmpty(responseText))
                    {
                        RemoveThinkingMessage();
                        AddMessage("MikuBot", CleanMessageContent(responseText), false);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"NativeWebChatWindow callback error: {ex}");
            }
        };

        isCallbackSetup = true;
        Debug.Log("NativeWebChatWindow: DialogProcessor callbacks setup complete");
    }

    void CreateNativeWebChatWindow()
    {
        hInstance = NativeWebChatAPI.GetModuleHandle(null);
        wndProcDelegate = new NativeWebChatAPI.WndProcDelegate(WindowProc);

        // Create brushes and fonts
        CreateUIResources();

        // Register window class
        NativeWebChatAPI.WNDCLASS wndClass = new NativeWebChatAPI.WNDCLASS();
        wndClass.style = 0;
        wndClass.lpfnWndProc = wndProcDelegate;
        wndClass.cbClsExtra = 0;
        wndClass.cbWndExtra = 0;
        wndClass.hInstance = hInstance;
        wndClass.hIcon = IntPtr.Zero;
        wndClass.hCursor = NativeWebChatAPI.LoadCursor(IntPtr.Zero, NativeWebChatAPI.IDC_ARROW);
        wndClass.hbrBackground = grayBrush;
        wndClass.lpszMenuName = null;
        wndClass.lpszClassName = className;

        ushort classAtom = NativeWebChatAPI.RegisterClass(ref wndClass);
        if (classAtom == 0)
        {
            int error = Marshal.GetLastWin32Error();
            Debug.LogError($"NativeWebChatWindow: Failed to register window class. Error: {error}");
            return;
        }

        // Create main window
        chatWindowHandle = NativeWebChatAPI.CreateWindowEx(
            0, className, windowTitle,
            NativeWebChatAPI.WS_OVERLAPPEDWINDOW,
            300, 200, windowWidth, windowHeight,
            IntPtr.Zero, IntPtr.Zero, hInstance, IntPtr.Zero);

        if (chatWindowHandle == IntPtr.Zero)
        {
            int error = Marshal.GetLastWin32Error();
            Debug.LogError($"NativeWebChatWindow: Failed to create chat window. Error: {error}");
            return;
        }

        CreateNativeWebControls();
        isWindowCreated = true;
        
        // Add welcome message
        AddMessage("MikuBot", "안녕하세요! 무엇을 도와드릴까요? 😊", false);
        
        Debug.Log("NativeWebChatWindow: Native web chat window created successfully");
    }

    void CreateUIResources()
    {
        // Create brushes
        pinkBrush = NativeWebChatAPI.CreateSolidBrush(NativeWebChatAPI.COLOR_USER_BUBBLE);
        blueBrush = NativeWebChatAPI.CreateSolidBrush(NativeWebChatAPI.COLOR_BOT_BUBBLE);
        grayBrush = NativeWebChatAPI.CreateSolidBrush(NativeWebChatAPI.COLOR_BACKGROUND);
        whiteBrush = NativeWebChatAPI.CreateSolidBrush(NativeWebChatAPI.COLOR_WHITE);

        // Create fonts
        headerFont = NativeWebChatAPI.CreateFont(
            -20, 0, 0, 0, 700, // Height=-20, Bold
            0, 0, 0, 129, 3, 2, 1, 49,
            "맑은 고딕");

        messageFont = NativeWebChatAPI.CreateFont(
            -14, 0, 0, 0, 400, // Height=-14, Normal
            0, 0, 0, 129, 3, 2, 1, 49,
            "맑은 고딕");
    }

    void CreateNativeWebControls()
    {
        int margin = 10;
        int headerHeight = 60;
        int inputHeight = 50;
        int statusHeight = 25;
        int buttonWidth = 80;

        // Header area (custom painted)
        headerHandle = NativeWebChatAPI.CreateWindowEx(
            0, "STATIC", "🤖 MikuBot Assistant             🟢 Online",
            NativeWebChatAPI.WS_CHILD | NativeWebChatAPI.WS_VISIBLE,
            0, 0, windowWidth, headerHeight,
            chatWindowHandle, new IntPtr(NativeWebChatAPI.ID_HEADER), hInstance, IntPtr.Zero);

        // Chat display area
        chatDisplayHandle = NativeWebChatAPI.CreateWindowEx(
            0, "EDIT", "",
            NativeWebChatAPI.WS_CHILD | NativeWebChatAPI.WS_VISIBLE | NativeWebChatAPI.WS_BORDER |
            NativeWebChatAPI.ES_MULTILINE | NativeWebChatAPI.ES_READONLY | NativeWebChatAPI.ES_AUTOVSCROLL | 
            NativeWebChatAPI.WS_VSCROLL,
            margin, headerHeight + margin, 
            windowWidth - 20, windowHeight - headerHeight - inputHeight - statusHeight - 60,
            chatWindowHandle, new IntPtr(NativeWebChatAPI.ID_CHAT_DISPLAY), hInstance, IntPtr.Zero);

        // Chat input field
        chatInputHandle = NativeWebChatAPI.CreateWindowEx(
            0, "EDIT", "",
            NativeWebChatAPI.WS_CHILD | NativeWebChatAPI.WS_VISIBLE | NativeWebChatAPI.WS_BORDER |
            NativeWebChatAPI.ES_MULTILINE | NativeWebChatAPI.ES_AUTOVSCROLL,
            margin, windowHeight - inputHeight - statusHeight - 40, 
            windowWidth - buttonWidth - 30, inputHeight,
            chatWindowHandle, new IntPtr(NativeWebChatAPI.ID_CHAT_INPUT), hInstance, IntPtr.Zero);

        // Send button
        sendButtonHandle = NativeWebChatAPI.CreateWindowEx(
            0, "BUTTON", "💌 전송",
            NativeWebChatAPI.WS_CHILD | NativeWebChatAPI.WS_VISIBLE,
            windowWidth - buttonWidth - 10, windowHeight - inputHeight - statusHeight - 40, 
            buttonWidth, inputHeight,
            chatWindowHandle, new IntPtr(NativeWebChatAPI.ID_SEND_BUTTON), hInstance, IntPtr.Zero);

        // Status bar
        statusHandle = NativeWebChatAPI.CreateWindowEx(
            0, "STATIC", "Enter를 눌러서 전송하세요",
            NativeWebChatAPI.WS_CHILD | NativeWebChatAPI.WS_VISIBLE,
            margin, windowHeight - statusHeight - 10, 
            windowWidth - 20, statusHeight,
            chatWindowHandle, new IntPtr(NativeWebChatAPI.ID_STATUS), hInstance, IntPtr.Zero);

        ApplyModernStyling();
        UpdateChatDisplay();
    }

    void ApplyModernStyling()
    {
        // Apply fonts
        if (headerFont != IntPtr.Zero && headerHandle != IntPtr.Zero)
            NativeWebChatAPI.SendMessage(headerHandle, NativeWebChatAPI.WM_SETFONT, headerFont, new IntPtr(1));

        if (messageFont != IntPtr.Zero)
        {
            if (chatDisplayHandle != IntPtr.Zero)
                NativeWebChatAPI.SendMessage(chatDisplayHandle, NativeWebChatAPI.WM_SETFONT, messageFont, new IntPtr(1));
            
            if (chatInputHandle != IntPtr.Zero)
                NativeWebChatAPI.SendMessage(chatInputHandle, NativeWebChatAPI.WM_SETFONT, messageFont, new IntPtr(1));
            
            if (sendButtonHandle != IntPtr.Zero)
                NativeWebChatAPI.SendMessage(sendButtonHandle, NativeWebChatAPI.WM_SETFONT, messageFont, new IntPtr(1));
            
            if (statusHandle != IntPtr.Zero)
                NativeWebChatAPI.SendMessage(statusHandle, NativeWebChatAPI.WM_SETFONT, messageFont, new IntPtr(1));
        }
    }

    IntPtr WindowProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam)
    {
        switch (msg)
        {
            case NativeWebChatAPI.WM_COMMAND:
                HandleButtonClick((int)wParam);
                break;

            case NativeWebChatAPI.WM_CLOSE:
                HideChatWindow();
                return IntPtr.Zero;

            case NativeWebChatAPI.WM_DESTROY:
                return IntPtr.Zero;

            case 0x0100: // WM_KEYDOWN
                if ((int)wParam == 13 && lParam == chatInputHandle) // Enter key
                {
                    SendMessage();
                    return IntPtr.Zero;
                }
                break;
        }

        return NativeWebChatAPI.DefWindowProc(hWnd, msg, wParam, lParam);
    }

    void HandleButtonClick(int buttonId)
    {
        switch (buttonId)
        {
            case NativeWebChatAPI.ID_SEND_BUTTON:
                SendMessage();
                break;
        }
    }

    void SendMessage()
    {
        if (chatInputHandle == IntPtr.Zero || dialogProcessor == null) return;

        int textLength = (int)NativeWebChatAPI.SendMessage(chatInputHandle, NativeWebChatAPI.WM_GETTEXTLENGTH, IntPtr.Zero, IntPtr.Zero);
        if (textLength == 0) return;

        StringBuilder inputText = new StringBuilder(textLength + 1);
        int actualLength = NativeWebChatAPI.GetWindowText(chatInputHandle, inputText, textLength + 1);
        
        string message = inputText.ToString().Trim();
        if (string.IsNullOrEmpty(message)) return;

        // Clear input field
        NativeWebChatAPI.SendMessage(chatInputHandle, NativeWebChatAPI.WM_SETTEXT, IntPtr.Zero, "");

        // Add user message
        AddMessage("사용자", message, true);

        // Process message
        ProcessMessageAsync(message);

        // Focus back to input
        NativeWebChatAPI.SetFocus(chatInputHandle);
    }

    async void ProcessMessageAsync(string message)
    {
        try
        {
            AddMessage("MikuBot", "생각중... 🤔", false);
            UpdateStatus("MikuBot이 응답 중...");

            var payloads = new Dictionary<string, object>();
            await dialogProcessor.StartDialogAsync(message, payloads);
            
            await UniTask.Delay(1000);
            
            if (IsLastMessageThinking())
            {
                RemoveThinkingMessage();
                AddMessage("MikuBot", "응답이 처리되었습니다. 음성 및 애니메이션을 확인해주세요! ✨", false);
            }

            UpdateStatus("Enter를 눌러서 전송하세요");
        }
        catch (Exception ex)
        {
            RemoveThinkingMessage();
            AddMessage("MikuBot", $"오류가 발생했습니다: {ex.Message} ❌", false);
            UpdateStatus("오류 발생");
            Debug.LogError($"NativeWebChatWindow ProcessMessageAsync error: {ex}");
        }
    }

    void AddMessage(string sender, string content, bool isUser)
    {
        messages.Add(new ChatMessage(sender, content, isUser));
        UpdateChatDisplay();
    }

    void RemoveThinkingMessage()
    {
        if (messages.Count > 0 && messages[messages.Count - 1].content.Contains("생각중"))
        {
            messages.RemoveAt(messages.Count - 1);
            UpdateChatDisplay();
        }
    }

    bool IsLastMessageThinking()
    {
        return messages.Count > 0 && messages[messages.Count - 1].content.Contains("생각중");
    }

    void UpdateChatDisplay()
    {
        if (chatDisplayHandle == IntPtr.Zero) return;

        StringBuilder chatContent = new StringBuilder();
        
        foreach (var message in messages)
        {
            chatContent.Append(message.GetDisplayText());
            chatContent.AppendLine();
        }

        NativeWebChatAPI.SendMessage(chatDisplayHandle, NativeWebChatAPI.WM_SETTEXT, IntPtr.Zero, chatContent.ToString());

        // Scroll to bottom
        int textLength = chatContent.Length;
        NativeWebChatAPI.SendMessage(chatDisplayHandle, NativeWebChatAPI.EM_SETSEL, new IntPtr(textLength), new IntPtr(textLength));
    }

    void UpdateStatus(string status)
    {
        if (statusHandle != IntPtr.Zero)
        {
            NativeWebChatAPI.SendMessage(statusHandle, NativeWebChatAPI.WM_SETTEXT, IntPtr.Zero, status);
        }
    }

    string CleanMessageContent(string content)
    {
        if (string.IsNullOrEmpty(content)) return content;

        // Remove language tags, face tags, animation tags
        content = System.Text.RegularExpressions.Regex.Replace(content, @"\[lang:\w+\]", "");
        content = System.Text.RegularExpressions.Regex.Replace(content, @"\[face:\w+\]", "");
        content = System.Text.RegularExpressions.Regex.Replace(content, @"\[(?:anim|animation):\w+\]", "");
        content = System.Text.RegularExpressions.Regex.Replace(content, @"\s+", " ");
        
        return content.Trim();
    }

    public void ShowChatWindow()
    {
        // Chrome 앱 모드로 HTML 채팅창 실행
        LaunchChromeAppMode();
    }

    void LaunchChromeAppMode()
    {
        string htmlFilePath = System.IO.Path.Combine(Application.streamingAssetsPath, "chat-ui.html");
        
        // 절대 경로로 변환 (WSL 경로 문제 해결)
        htmlFilePath = System.IO.Path.GetFullPath(htmlFilePath);
        
        Debug.Log($"NativeWebChatWindow: Looking for HTML file at: {htmlFilePath}");
        
        if (!System.IO.File.Exists(htmlFilePath))
        {
            Debug.LogError("NativeWebChatWindow: HTML file not found at " + htmlFilePath);
            return;
        }

        try
        {
            // Chrome 실행 파일 경로 찾기
            string chromePath = FindChromeExecutable();
            
            if (string.IsNullOrEmpty(chromePath))
            {
                Debug.LogWarning("NativeWebChatWindow: Chrome not found, using default browser");
                LaunchDefaultBrowser(htmlFilePath);
                return;
            }

            // 파일 URI 생성 (올바른 형식으로)
            string fileUri = new System.Uri(htmlFilePath).AbsoluteUri;
            Debug.Log($"NativeWebChatWindow: File URI: {fileUri}");
            
            // Chrome 앱 모드 실행 (더 안전한 인수)
            string chromeArgs = $"--app={fileUri} --window-size={windowWidth},{windowHeight} --window-position=300,200 --user-data-dir=\"{GetChromeUserDataDir()}\"";
            
            Debug.Log($"NativeWebChatWindow: Launching Chrome with args: {chromeArgs}");
            
            System.Diagnostics.ProcessStartInfo startInfo = new System.Diagnostics.ProcessStartInfo
            {
                FileName = chromePath,
                Arguments = chromeArgs,
                UseShellExecute = false,
                CreateNoWindow = false,
                WorkingDirectory = System.IO.Path.GetDirectoryName(htmlFilePath)
            };

            System.Diagnostics.Process chromeProcess = System.Diagnostics.Process.Start(startInfo);
            
            if (chromeProcess != null)
            {
                Debug.Log($"NativeWebChatWindow: Chrome app mode launched successfully (PID: {chromeProcess.Id})");
            }
            else
            {
                Debug.LogError("NativeWebChatWindow: Failed to start Chrome app mode");
                LaunchDefaultBrowser(htmlFilePath);
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"NativeWebChatWindow: Exception launching Chrome app mode: {ex.Message}");
            LaunchDefaultBrowser(htmlFilePath);
        }
    }

    string GetChromeUserDataDir()
    {
        // 임시 사용자 데이터 디렉토리 (격리된 환경)
        string tempDir = System.IO.Path.Combine(Application.persistentDataPath, "ChromeAppData");
        if (!System.IO.Directory.Exists(tempDir))
        {
            System.IO.Directory.CreateDirectory(tempDir);
        }
        return tempDir;
    }

    string FindChromeExecutable()
    {
        // Chrome 설치 경로들을 순서대로 확인
        string[] chromePaths = {
            @"C:\Program Files\Google\Chrome\Application\chrome.exe",
            @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            System.IO.Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData), 
                @"Google\Chrome\Application\chrome.exe"),
            System.IO.Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFiles), 
                @"Google\Chrome\Application\chrome.exe")
        };

        foreach (string path in chromePaths)
        {
            if (System.IO.File.Exists(path))
            {
                Debug.Log($"NativeWebChatWindow: Found Chrome at {path}");
                return path;
            }
        }

        // 환경변수 PATH에서 chrome 찾기
        try
        {
            var pathVariable = System.Environment.GetEnvironmentVariable("PATH");
            if (!string.IsNullOrEmpty(pathVariable))
            {
                var paths = pathVariable.Split(';');
                foreach (var path in paths)
                {
                    var chromePath = System.IO.Path.Combine(path.Trim(), "chrome.exe");
                    if (System.IO.File.Exists(chromePath))
                    {
                        Debug.Log($"NativeWebChatWindow: Found Chrome in PATH at {chromePath}");
                        return chromePath;
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"NativeWebChatWindow: Error searching Chrome in PATH: {ex.Message}");
        }

        Debug.LogWarning("NativeWebChatWindow: Chrome executable not found");
        return null;
    }

    void LaunchDefaultBrowser(string htmlFilePath)
    {
        try
        {
            string fileUri = "file:///" + htmlFilePath.Replace("\\", "/");
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = fileUri,
                UseShellExecute = true
            });
            Debug.Log("NativeWebChatWindow: Opened in default browser (fallback)");
        }
        catch (Exception ex)
        {
            Debug.LogError($"NativeWebChatWindow: Failed to open in default browser: {ex.Message}");
        }
    }

    public void HideChatWindow()
    {
        if (isWindowCreated && chatWindowHandle != IntPtr.Zero)
        {
            NativeWebChatAPI.ShowWindow(chatWindowHandle, NativeWebChatAPI.SW_HIDE);
        }
    }

    void OnDestroy()
    {
#if UNITY_STANDALONE_WIN
        if (chatWindowHandle != IntPtr.Zero)
        {
            NativeWebChatAPI.DestroyWindow(chatWindowHandle);
        }

        // Clean up resources
        if (pinkBrush != IntPtr.Zero) NativeWebChatAPI.DeleteObject(pinkBrush);
        if (blueBrush != IntPtr.Zero) NativeWebChatAPI.DeleteObject(blueBrush);
        if (grayBrush != IntPtr.Zero) NativeWebChatAPI.DeleteObject(grayBrush);
        if (whiteBrush != IntPtr.Zero) NativeWebChatAPI.DeleteObject(whiteBrush);
        if (headerFont != IntPtr.Zero) NativeWebChatAPI.DeleteObject(headerFont);
        if (messageFont != IntPtr.Zero) NativeWebChatAPI.DeleteObject(messageFont);
#endif
    }
}