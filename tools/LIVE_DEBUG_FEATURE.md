# ScyllaDB Cloud I/O Benchmark - Live Debug Output Feature

## New Feature: Real-time Command Output Streaming ✨

You can now see the actual output from the ScyllaDB I/O setup script as it runs on the cloud instances in real-time!

## Usage 🚀

### Basic Debug Mode
```bash
python3 cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-0abcd1234 \
  --instance-types i4i.xlarge \
  --aws-key-name my-ec2-key \
  --runs 1 \
  --debug
```

### **NEW: Live Debug Mode** 🔴
```bash
python3 cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-0abcd1234 \
  --instance-types i4i.xlarge \
  --aws-key-name my-ec2-key \
  --runs 1 \
  --debug-live
```

## What You'll See with `--debug-live` 📟

When you use the `--debug-live` flag, you'll see real-time output like this:

```
🔴 LIVE OUTPUT from i-04c1bab3d7f7188b5 (scyllaadm@1.2.3.4):
============================================================
📟 Starting ScyllaDB Cloud I/O Setup...
📟 Checking instance type: i4i.xlarge
📟 Found 1 NVMe devices
📟 Reading AWS I/O parameters from /opt/scylladb/scylla-machine-image/aws_io_params.yaml
📟 Instance type i4i.xlarge found in parameters
📟 Calculating metrics for 1 disk(s)
📟   read_iops: 109954
📟   read_bandwidth: 763580096
📟   write_iops: 61008
📟   write_bandwidth: 561926784
📟 Writing metrics to /etc/scylla.d/io_properties.yaml
📟 Creating I/O configuration file /etc/scylla.d/io.conf
📟 Setup completed successfully
============================================================
🔴 LIVE OUTPUT COMPLETE (return code: 0)
```

## Benefits 💡

1. **Real-time Visibility**: See exactly what the `scylla_cloud_io_setup` script is doing
2. **Better Debugging**: Identify where issues occur during execution
3. **Progress Monitoring**: Watch long-running benchmarks in real-time
4. **Performance Insights**: See actual metric values as they're calculated

## How It Works 🔧

- **Regular `--debug`**: Shows debug logs but waits for command completion
- **New `--debug-live`**: Streams command output line-by-line as it happens
- Works with all cloud providers (AWS, GCP, Azure)
- Automatically merges stdout and stderr for cleaner output
- Uses emoji indicators (🔴 📟) to distinguish live output from regular logs

## Examples 📚

### Quick Test with Live Output
```bash
# Test a single instance type with live streaming
python3 cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-types i4i.xlarge \
  --runs 1 \
  --debug-live
```

### Multiple Instance Types with Live Debug
```bash
# Benchmark multiple types with live output
python3 cloud_io_benchmark.py \
  --cloud aws \
  --region us-east-1 \
  --image ami-12345678 \
  --instance-types i4i.large i4i.xlarge i4i.2xlarge \
  --runs 2 \
  --debug-live \
  --max-concurrent 1  # Run one at a time to avoid mixed output
```

### GCP with Live Output
```bash
python3 cloud_io_benchmark.py \
  --cloud gcp \
  --region us-central1 \
  --project-id my-project \
  --image projects/scylla-images/global/images/scylladb-5-2-1 \
  --instance-types n2-standard-4 \
  --debug-live
```

## Technical Implementation 🛠️

The live streaming feature:
- Uses `asyncio.create_subprocess_exec()` with `stdout=PIPE`
- Streams output line-by-line with `async for line in process.stdout`
- Merges stderr into stdout for cleaner real-time display
- Available in all cloud provider implementations (AWS, GCP, Azure)
- Controlled by global `DEBUG_LIVE_MODE` flag

## When to Use Each Mode 📋

| Mode | Use Case |
|------|----------|
| `--debug` | Development, troubleshooting after completion |
| `--debug-live` | Real-time monitoring, understanding script behavior, debugging stuck processes |
| Neither | Production runs, automated CI/CD |

## Tips 💭

1. **Use `--max-concurrent 1`** with `--debug-live` to avoid mixed output from multiple instances
2. **Perfect for troubleshooting** when metrics come back empty
3. **Great for learning** how the ScyllaDB I/O setup process works
4. **Ideal for long-running benchmarks** to monitor progress

Now you can see exactly what happens inside your ScyllaDB instances during I/O benchmarking! 🎉
