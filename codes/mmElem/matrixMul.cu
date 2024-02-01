/**
 * Copyright 1993-2015 NVIDIA Corporation.  All rights reserved.
 *
 * Please refer to the NVIDIA end user license agreement (EULA) associated
 * with this source code for terms and conditions that govern your use of
 * this software. Any use, reproduction, disclosure, or distribution of
 * this software and related documentation outside the terms of the EULA
 * is strictly prohibited.
 *
 */

/**
 * Matrix multiplication: C = A * B.
 * Host code.
 *
 * This sample implements matrix multiplication as described in Chapter 3
 * of the programming guide.
 * It has been written for clarity of exposition to illustrate various CUDA
 * programming principles, not with the goal of providing the most
 * performant generic kernel for matrix multiplication.
 *
 * See also:
 * V. Volkov and J. Demmel, "Benchmarking GPUs to tune dense linear algebra,"
 * in Proc. 2008 ACM/IEEE Conf. on Supercomputing (SC '08),
 * Piscataway, NJ: IEEE Press, 2008, pp. Art. 31:1-11.
 */

// System includes
#include <stdio.h>
#include <assert.h>

// CUDA runtime
#include <cuda_runtime.h>

// Helper functions and utilities to work with CUDA
#include <helper_functions.h>
#include <helper_cuda.h>
#include <omp.h>

#if BUILD_TIMER == 1
static double timer;
#endif

/**
 * Matrix multiplication (CUDA Kernel) on the device: C = A * B
 * wA is A's width and wB is B's width
 * Every thread computes one element of C as a dot product
 * C[i][j] = A[i][:] * B[:][j]
 */
__global__ void matrixMulCUDA(float *C, float *A, float *B, int ldA, int ldB, int ldC) {
   // Thread global indexes
   int i = blockIdx.y * blockDim.y + threadIdx.y;
   int j = blockIdx.x * blockDim.x + threadIdx.x;

//   printf("**C[%d][%d]\n", i, j);

   float *ptrA = &A[i*ldA]; // Pointer to the first element of row i of A

   float tmp = 0.0f;
   for (int k = 0; k < ldA; k++) {
     tmp += (*ptrA++) * B[k*ldB+j];
   }
   C[i*ldC+j] = tmp;
//   printf("C[%d][%d] = %f\n", i, j, tmp);

}


void constantInit(float *data, int size, float val) {
	for (int i = 0; i < size; ++i) {
		data[i] = val;
	}
}

double mysecond() {
	struct timeval tp;
	struct timezone tzp;
	int i = gettimeofday(&tp, &tzp);
	return ((double) tp.tv_sec + (double) tp.tv_usec * 1.e-6);
}

/**
 * Run a simple test of matrix multiplication using CUDA
 */
int matrixMultiply(int argc, char **argv, int block_size, dim3 &dimsA,
		dim3 &dimsB) {
	// Allocate host memory for matrices A and B
	unsigned int size_A = dimsA.x * dimsA.y;
	unsigned int mem_size_A = sizeof(float) * size_A;
	float *h_A = (float *) malloc(mem_size_A);
	unsigned int size_B = dimsB.x * dimsB.y;
	unsigned int mem_size_B = sizeof(float) * size_B;
	float *h_B = (float *) malloc(mem_size_B);

	// Initialize host memory
	const float valB = 0.01f;
	constantInit(h_A, size_A, 1.0f);
	constantInit(h_B, size_B, valB);

	// Allocate device memory
	float *d_A, *d_B, *d_C;

	// Allocate host matrix C
	dim3 dimsC(dimsB.x, dimsA.y, 1);
	unsigned int mem_size_C = dimsC.x * dimsC.y * sizeof(float);
	float *h_C = (float *) malloc(mem_size_C);

	if (h_C == NULL) {
		fprintf(stderr, "Failed to allocate host matrix C!\n");
		exit (EXIT_FAILURE);
	}

	cudaError_t error;

	error = cudaMalloc((void **) &d_A, mem_size_A);

	if (error != cudaSuccess) {
		printf("cudaMalloc d_A returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	error = cudaMalloc((void **) &d_B, mem_size_B);

	if (error != cudaSuccess) {
		printf("cudaMalloc d_B returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	error = cudaMalloc((void **) &d_C, mem_size_C);

	if (error != cudaSuccess) {
		printf("cudaMalloc d_C returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	// copy host memory to device
	error = cudaMemcpy(d_A, h_A, mem_size_A, cudaMemcpyHostToDevice);

	if (error != cudaSuccess) {
		printf("cudaMemcpy (d_A,h_A) returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	error = cudaMemcpy(d_B, h_B, mem_size_B, cudaMemcpyHostToDevice);

	if (error != cudaSuccess) {
		printf("cudaMemcpy (d_B,h_B) returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	// Setup execution parameters
	dim3 threads(block_size, block_size);
	dim3 grid(dimsB.x / threads.x, dimsA.y / threads.y);

	// Create and start timer
	printf("Computing result using CUDA Kernel...\n");

	// Performs warmup operation using matrixMul CUDA kernel
//	if (block_size == 16) {
//		matrixMulCUDA<16> <<<grid, threads>>>(d_C, d_A, d_B, dimsA.x, dimsB.x);
//	} else {
//		matrixMulCUDA<32> <<<grid, threads>>>(d_C, d_A, d_B, dimsA.x, dimsB.x);
//	}

//	printf("done\n");
//
//	cudaDeviceSynchronize();

	// Allocate CUDA events that we'll use for timing
	cudaEvent_t start;
	error = cudaEventCreate(&start);

	if (error != cudaSuccess) {
		fprintf(stderr, "Failed to create start event (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

	cudaEvent_t stop;
	error = cudaEventCreate(&stop);

	if (error != cudaSuccess) {
		fprintf(stderr, "Failed to create stop event (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

	// Record the start event
	error = cudaEventRecord(start, NULL);

	if (error != cudaSuccess) {
		fprintf(stderr, "Failed to record start event (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

	// Execute the kernel
	int nIter = 1;
#if BUILD_TIMER == 1
	printf("BEFORE START KERNEL %lf\n", mysecond() - timer);
	double t1 = mysecond();
#endif
	for (int j = 0; j < nIter; j++) {
		//matrixMulCUDA<32> <<<grid, threads>>>(d_C, d_A, d_B, dimsA.x, dimsB.x);
		matrixMulCUDA <<<grid, threads>>>(d_C, d_A, d_B, dimsA.x, dimsB.x, dimsC.x);

		cudaDeviceSynchronize();
	}

#if BUILD_TIMER == 1
	double exec_time = mysecond() - t1;
	printf("KERNEL EXECUTION TIME %lf\n", exec_time);
#endif

	// Record the stop event
	error = cudaEventRecord(stop, NULL);

	if (error != cudaSuccess) {
		fprintf(stderr, "Failed to record stop event (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

	// Wait for the stop event to complete
	error = cudaEventSynchronize(stop);

	if (error != cudaSuccess) {
		fprintf(stderr,
				"Failed to synchronize on the stop event (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

	float msecTotal = 0.0f;
	error = cudaEventElapsedTime(&msecTotal, start, stop);

	if (error != cudaSuccess) {
		fprintf(stderr,
				"Failed to get time elapsed between events (error code %s)!\n",
				cudaGetErrorString(error));
		exit (EXIT_FAILURE);
	}

#if BUILD_TIMER == 1
	// Compute and print the performance
	float msecPerMatrixMul = msecTotal / nIter;
	double flopsPerMatrixMul = 2.0 * (double) dimsA.x * (double) dimsA.y
			* (double) dimsB.x;
	double gigaFlops = (flopsPerMatrixMul * 1.0e-9f)
			/ (msecPerMatrixMul / 1000.0f);
	printf(
			"Performance= %.2f GFlop/s, Time= %.3f msec, Size= %.0f Ops, WorkgroupSize= %u threads/block\n",
			gigaFlops, msecPerMatrixMul, flopsPerMatrixMul,
			threads.x * threads.y);
#endif

	// Copy result from device to host
	error = cudaMemcpy(h_C, d_C, mem_size_C, cudaMemcpyDeviceToHost);

	if (error != cudaSuccess) {
		printf("cudaMemcpy (h_C,d_C) returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
		exit (EXIT_FAILURE);
	}

	printf("Checking computed result for correctness: ");
	bool correct = true;

	// test relative error by the formula
	//     |<x, y>_cpu - <x,y>_gpu|/<|x|, |y|>  < eps
	double eps = 1.e-6; // machine zero
#if BUILD_TIMER == 1
	t1 = mysecond();
#endif

#pragma omp parallel for shared(h_C, correct)
	for (int i = 0; i < (int) (dimsC.x * dimsC.y); i++) {
		float abs_err = fabs(h_C[i] - float(dimsA.x * valB));
		float dot_length = dimsA.x;
		float abs_val = fabs(h_C[i]);
		float rel_err = abs_err / abs_val / dot_length;

		if (rel_err > eps) {
			printf("Error! Matrix[%05d]=%.8f, ref=%.8f error term is > %E\n", i,
					h_C[i], dimsA.x * valB, eps);
#pragma omp critical
			{
				correct = false;
			}
		}
	}

#if BUILD_TIMER == 1
	exec_time = mysecond() - t1;
	printf("CMP TIME %lf\n", exec_time);
#endif
	printf("%s\n", correct ? "Result = PASS" : "Result = FAIL");

	// Clean up memory
	free(h_A);
	free(h_B);
	free(h_C);
	cudaFree(d_A);
	cudaFree(d_B);
	cudaFree(d_C);

	printf(
			"\nNOTE: The CUDA Samples are not meant for performance measurements. "
					"Results may vary when GPU Boost is enabled.\n");

	if (correct) {
		return EXIT_SUCCESS;
	} else {
		return EXIT_FAILURE;
	}
}

/**
 * Program main
 */
int main(int argc, char **argv) {
#if BUILD_TIMER == 1
	timer = mysecond();
#endif
	printf("[Matrix Multiply Using CUDA] - Starting...\n");

	if (checkCmdLineFlag(argc, (const char **) argv, "help")
			|| checkCmdLineFlag(argc, (const char **) argv, "?")) {
		printf("Usage -device=n (n >= 0 for deviceID)\n");
		printf("      -wA=WidthA -hA=HeightA (Width x Height of Matrix A)\n");
		printf("      -wB=WidthB -hB=HeightB (Width x Height of Matrix B)\n");
		printf(
				"  Note: Outer matrix dimensions of A & B matrices must be equal.\n");

		exit (EXIT_SUCCESS);
	}

	// By default, we use device 0, otherwise we override the device ID based on what is provided at the command line
	int devID = 0;

	if (checkCmdLineFlag(argc, (const char **) argv, "device")) {
		devID = getCmdLineArgumentInt(argc, (const char **) argv, "device");
		cudaSetDevice(devID);
	}

	cudaError_t error;
	cudaDeviceProp deviceProp;
	error = cudaGetDevice(&devID);

	if (error != cudaSuccess) {
		printf("cudaGetDevice returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
	}

	error = cudaGetDeviceProperties(&deviceProp, devID);

	if (deviceProp.computeMode == cudaComputeModeProhibited) {
		fprintf(stderr,
				"Error: device is running in <Compute Mode Prohibited>, no threads can use ::cudaSetDevice().\n");
		exit (EXIT_SUCCESS);
	}

	if (error != cudaSuccess) {
		printf(
				"cudaGetDeviceProperties returned error %s (code %d), line(%d)\n",
				cudaGetErrorString(error), error, __LINE__);
	} else {
		printf("GPU Device %d: \"%s\" with compute capability %d.%d\n\n", devID,
				deviceProp.name, deviceProp.major, deviceProp.minor);
	}

	// Use a larger block size for Fermi and above
	int block_size = (deviceProp.major < 2) ? 16 : 32;

	dim3 dimsA(5 * 2 * block_size, 5 * 2 * block_size, 1);
	dim3 dimsB(5 * 4 * block_size, 5 * 2 * block_size, 1);

	// width of Matrix A
	if (checkCmdLineFlag(argc, (const char **) argv, "wA")) {
		dimsA.x = getCmdLineArgumentInt(argc, (const char **) argv, "wA");
	}

	// height of Matrix A
	if (checkCmdLineFlag(argc, (const char **) argv, "hA")) {
		dimsA.y = getCmdLineArgumentInt(argc, (const char **) argv, "hA");
	}

	// width of Matrix B
	if (checkCmdLineFlag(argc, (const char **) argv, "wB")) {
		dimsB.x = getCmdLineArgumentInt(argc, (const char **) argv, "wB");
	}

	// height of Matrix B
	if (checkCmdLineFlag(argc, (const char **) argv, "hB")) {
		dimsB.y = getCmdLineArgumentInt(argc, (const char **) argv, "hB");
	}

	if (dimsA.x != dimsB.y) {
		printf("Error: outer matrix dimensions must be equal. (%d != %d)\n",
				dimsA.x, dimsB.y);
		exit (EXIT_FAILURE);
	}

	printf("MatrixA(%d,%d), MatrixB(%d,%d)\n", dimsA.x, dimsA.y, dimsB.x,
			dimsB.y);

	int matrix_result = matrixMultiply(argc, argv, block_size, dimsA, dimsB);

	exit(matrix_result);
}
