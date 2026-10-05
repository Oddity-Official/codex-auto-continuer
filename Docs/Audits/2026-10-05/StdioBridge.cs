// Probe-only transport adapter. No JSON interpretation or response synthesis.
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

class StdioBridge {
    static int Main(string[] args) {
        if (!args.Contains("app-server")) {
            var start = new ProcessStartInfo(Environment.GetEnvironmentVariable("CAC_BRIDGE_NATIVE_CODEX"));
            start.Arguments = string.Join(" ", args.Select(x => "\"" + x.Replace("\"", "\\\"") + "\""));
            start.UseShellExecute = false;
            using (var child = Process.Start(start)) { child.WaitForExit(); return child.ExitCode; }
        }
        try { Run().GetAwaiter().GetResult(); return 0; }
        catch (Exception error) { Console.Error.WriteLine("CAC probe bridge: " + error.GetType().Name); return 1; }
    }

    static async Task Run() {
        using (var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(60)))
        using (var ws = new ClientWebSocket()) {
            ws.Options.Proxy = null;
            await ws.ConnectAsync(new Uri(Environment.GetEnvironmentVariable("CAC_OWNER_WS_URL")), cancel.Token);
            var input = Task.Run(async () => {
                string line;
                while ((line = Console.ReadLine()) != null) {
                    var bytes = Encoding.UTF8.GetBytes(line);
                    await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancel.Token);
                }
            });
            var output = Task.Run(async () => {
                var bytes = new byte[65536];
                using (var message = new MemoryStream()) {
                    while (!cancel.IsCancellationRequested) {
                        var received = await ws.ReceiveAsync(new ArraySegment<byte>(bytes), cancel.Token);
                        if (received.MessageType == WebSocketMessageType.Close) return;
                        message.Write(bytes, 0, received.Count);
                        if (message.Length > 16 * 1024 * 1024) throw new InvalidDataException();
                        if (received.EndOfMessage) {
                            Console.WriteLine(Encoding.UTF8.GetString(message.ToArray()));
                            Console.Out.Flush();
                            message.SetLength(0);
                        }
                    }
                }
            });
            var completed = await Task.WhenAny(input, output);
            await completed;
            cancel.Cancel();
        }
    }
}
