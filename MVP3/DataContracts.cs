using System.Text.Json.Serialization;

namespace Mvp3;

public sealed class SparseDctModel
{
    [JsonPropertyName("format")]
    public string Format { get; set; } = "sparse-orthonormal-dct-2d-v1";

    [JsonPropertyName("width")]
    public int Width { get; set; }

    [JsonPropertyName("height")]
    public int Height { get; set; }

    [JsonPropertyName("sample_count")]
    public int SampleCount { get; set; }

    [JsonPropertyName("content_threshold")]
    public int ContentThreshold { get; set; } = 128;

    [JsonPropertyName("coefficient_count")]
    public int CoefficientCount => Coefficients.Count;

    [JsonPropertyName("coefficients")]
    public List<DctCoefficient> Coefficients { get; set; } = [];
}

public sealed class DctCoefficient
{
    [JsonPropertyName("u")]
    public int U { get; set; }

    [JsonPropertyName("v")]
    public int V { get; set; }

    [JsonPropertyName("value")]
    public double Value { get; set; }
}

public sealed class ImageData(int width, int height, byte[] pixels)
{
    public int Width { get; } = width;
    public int Height { get; } = height;
    public byte[] Pixels { get; } = pixels;
}

public sealed record ErrorMetrics(double Mae, double Rmse, double[] Percentiles);
