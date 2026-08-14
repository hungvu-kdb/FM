using Mvp3;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            if (args.Length == 0 || args[0] is "-h" or "--help" or "help")
            {
                PrintHelp();
                return 0;
            }

            return args[0].ToLowerInvariant() switch
            {
                "analyze" => RunAnalyze(args[1..]),
                "apply" => RunApply(args[1..]),
                "validate" => RunValidate(args[1..]),
                _ => throw new ArgumentException($"Unknown command '{args[0]}'.")
            };
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"ERROR: {ex.Message}");
            return 1;
        }
    }

    private static int RunAnalyze(string[] args)
    {
        string root = args.FirstOrDefault(a => !a.StartsWith('-'))
            ?? Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, "..", "Root"));
        string output = GetOption(args, "--output") ?? Environment.CurrentDirectory;
        int max = int.Parse(GetOption(args, "--max-coefficients") ?? "16000");
        double target = double.Parse(GetOption(args, "--target-mae") ?? "1.433060",
            System.Globalization.CultureInfo.InvariantCulture);
        Analyzer.Run(root, output, max, target);
        return 0;
    }
