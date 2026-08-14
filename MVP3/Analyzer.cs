using System.Text.Json;

namespace Mvp3;

public static class Analyzer
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public static void Run(string rootDirectory, string outputDirectory, int maxCoefficients,
        double targetMae)
    {
        if (!Directory.Exists(rootDirectory))
            throw new DirectoryNotFoundException($"Root directory not found: {rootDirectory}");
        if (maxCoefficients < 1 || maxCoefficients >= 260 * 310)
            throw new ArgumentOutOfRangeException(nameof(maxCoefficients),
                "Coefficient budget must be between 1 and 80,599.");

        string[] paths = Directory.GetFiles(rootDirectory, "*.png")
            .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase).ToArray();
        if (paths.Length == 0)
            throw new InvalidOperationException("No PNG samples were found.");

        Console.WriteLine($"Loading {paths.Length} training PNGs...");
        byte[][] alphaSamples = new byte[paths.Length][];
        const int width = 260;
        const int height = 310;
        for (int i = 0; i < paths.Length; i++)
        {
            ImageData image = ImageIo.Load(paths[i]);
            if (image.Width != width || image.Height != height)
                throw new InvalidDataException($"{paths[i]} is {image.Width}x{image.Height}; expected 260x310.");
            alphaSamples[i] = ExtractAlpha(image);
        }

        double[] robustAlpha = CoordinateMedian(alphaSamples, width * height);
        Console.WriteLine("Computing orthonormal separable 2-D DCT...");
        double[] fullCoefficients = DctModel.Forward(robustAlpha, width, height);
        int[] ranked = Enumerable.Range(0, fullCoefficients.Length)
            .OrderByDescending(i => Math.Abs(fullCoefficients[i])).ToArray();

        int[] candidates = CandidateCounts(maxCoefficients);
        int selectedCount = maxCoefficients;
        double[]? selectedReconstruction = null;
        var trials = new List<object>();
        foreach (int count in candidates)
        {
            double[] sparse = new double[fullCoefficients.Length];
            for (int i = 0; i < count; i++)
                sparse[ranked[i]] = fullCoefficients[ranked[i]];
            double[] reconstruction = DctModel.Inverse(sparse, width, height);
            byte[] quantized = Quantize(reconstruction);
            ErrorMetrics metrics = ComputeMetrics(alphaSamples, quantized);
            trials.Add(new { coefficient_count = count, global_alpha_mae = metrics.Mae,
                global_alpha_rmse = metrics.Rmse });
            Console.WriteLine($"  {count,5} coefficients: MAE {metrics.Mae:F6}");
            selectedCount = count;
            selectedReconstruction = reconstruction;
            if (metrics.Mae <= targetMae)
                break;
        }
